#!/usr/bin/env python3
"""Plano reversível conjunto. Preparar não instala, publica nem reinicia nada."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


transaction = module('transacao_anterior', ROOT / 'operação/fechamento-2.0.py')
editor = module('somas_editores', ROOT / 'operação/preparar-editores-portal.py')
sha = transaction.sha


def versions(source):
    v = json.loads((source / 'operação/conjunto-versoes.json').read_text())
    if v.get('formato') != 1:
        raise ValueError('Formato de publicação incompatível')
    for name in ('nucleo', 'sls', 'bibliotecas', 'vscode', 'sublime'):
        if not re.fullmatch(r'\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?', v.get(name, '')):
            raise ValueError('Versão de publicação inválida: ' + name)
    return v


def cache(text, version):
    base = '/estático/wasm/' + version + '/'
    text = re.sub(r'/estático/wasm/(?:[0-9][A-Za-z0-9.-]*/)?(?=santafe\.(?:js|wasm)|["\']\s*\+\s*path\b)', base, text)
    return re.sub(r'(?<=src=")santafe\.js(?:\?v=[^"<>]*)?', base + 'santafe.js', text)


def page(text, v):
    marker = 'ap.rota("GET", "/baixar", função(req, res)'
    if text.count(marker) != 1:
        raise ValueError('Rota /baixar inesperada')
    start = text.index(marker)
    next_route = re.search(r'(?m)^ap\.rota\(', text[start + len(marker):])
    if not next_route:
        raise ValueError('Fim da rota não encontrado')
    end = start + len(marker) + next_route.start()
    part = text[start:end]
    current = re.findall(r'<h5[^>]*>Santafé (\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?)</h5>', part)
    if current != ['2.0.3'] and current != [v['nucleo']]:
        raise ValueError('Versão de portal inesperada; preserve edições locais')
    part = part.replace(current[0], v['nucleo'])
    for extension in ('tar.gz', 'zip'):
        if 'santafe-' + v['nucleo'] + '.' + extension not in part:
            raise ValueError('Download de núcleo ausente')
    part, count = re.subn(r'santafe-vscode-[0-9.]+\.vsix', 'santafe-vscode-' + v['vscode'] + '.vsix', part)
    if count != 2:
        raise ValueError('Número inesperado de links VSIX')
    part = editor.troque_unico(part, r'Santafe\.sublime-package\?v=[0-9.]+',
                              'Santafe.sublime-package?v=' + v['sublime'])
    part = editor.troque_unico(part, r'<p>Extensão oficial [0-9.]+:.*?</p>',
        '<p>Extensão oficial ' + v['vscode'] + ': gabaritos Unicode compostos e combinados, paleta suave HTML/JS e integração semântica com o SLS: conclusões, navegação, referências, renomeação, assinaturas e recuo.</p>')
    part = editor.troque_unico(part, r'<p>Pacote oficial [0-9.]+ para arquivos.*?</p>',
        '<p>Pacote oficial ' + v['sublime'] + ' para arquivos <code>.fé</code>: gabaritos Unicode, realce HTML/JS, snippets, execução e integração semântica pelo cliente LSP do Sublime.</p>')
    part = part.replace('A versão estável 2.0 inclui', 'A versão ' + v['nucleo'] + ' inclui')
    details = ('      <div id="bibliotecas-distribuicao" class="card-panel">\n'
               '        <strong>SLS ' + v['sls'] + ' e Bibliotecas ' + v['bibliotecas'] + '</strong>\n'
               '        <p>Instale núcleo e ferramentas juntos. O SLS analisa sem executar; '
               'as bibliotecas são instaladas por projeto, com lock e integridade. '
               'macOS e Linux; Windows ainda não homologado. Código C exige autorização explícita.</p>\n'
               '        <p><a href="/est%C3%A1tico/bibliotecas/v1/">Catálogo de bibliotecas</a> · '
               '<a href="/est%C3%A1tico/manual/#bibliotecas-projeto">Como instalar</a></p>\n'
               '      </div>\n')
    if 'id="bibliotecas-distribuicao"' in part:
        part = editor.troque_unico(part, r'      <div id="bibliotecas-distribuicao".*?</div>\n', details)
    else:
        marker2 = '      <h5 style="margin-top:32px">Instalação</h5>'
        if part.count(marker2) != 1:
            raise ValueError('Seção de instalação inesperada')
        part = part.replace(marker2, details + '\n' + marker2)
    return cache(text[:start] + part + text[end:], v['nucleo'])


def validate_editors(source, v):
    vs = source / 'extensões/vscode/dist' / ('santafe-' + v['vscode'] + '.vsix')
    su = source / 'extensões/sublime/dist/Santafe.sublime-package'
    pc = source / 'extensões/sublime/dist' / ('Santafe-' + v['sublime'] + '.sublime-package')
    with zipfile.ZipFile(vs) as z:
        if z.testzip() or json.loads(z.read('extension/package.json'))['version'] != v['vscode']:
            raise ValueError('VSIX inválido')
        for name in ('provedores-sls.js', 'realce-embutido.js', 'extension.js'):
            if z.read('extension/' + name) != (source / 'extensões/vscode' / name).read_bytes():
                raise ValueError('VSIX desatualizado: ' + name)
    with zipfile.ZipFile(su) as a, zipfile.ZipFile(pc) as b:
        if a.testzip() or b.testzip() or json.loads(a.read('package-metadata.json'))['version'] != v['sublime']:
            raise ValueError('Sublime inválido')
        if set(a.namelist()) != set(b.namelist()) | {'package-metadata.json'}:
            raise ValueError('Pacotes Sublime divergentes')
        for name in b.namelist():
            if a.read(name) != b.read(name) or a.read(name) != (source / 'extensões/sublime' / name).read_bytes():
                raise ValueError('Sublime desatualizado: ' + name)
        if not all(stat.S_ISREG(x.external_attr >> 16) for x in a.infolist()):
            raise ValueError('Entradas Sublime sem tipo regular')
    return vs, su, pc


def prepare(source, snapshot, prefix, downloads, registry, system, site, public, app, out, owner='rafael'):
    source, snapshot, prefix, downloads, registry = [p.resolve() for p in (source,snapshot,prefix,downloads,registry)]
    v = versions(source)
    if app.read_bytes() != (site / 'sfdev.fé').read_bytes():
        raise ValueError('Portal e fonte divergem; preservar edição local')
    out.mkdir(parents=True, exist_ok=False)
    entries = []
    def add(src, dst, who='root:root', mode=0o644, immutable=False):
        transaction.safe_destination(dst)
        if src.is_symlink() or not src.is_file():
            raise ValueError('Origem irregular: ' + str(src))
        if immutable and dst.exists() and sha(src) != sha(dst):
            raise ValueError('Versão imutável alterada: ' + str(dst))
        old = dst.stat() if dst.exists() else None
        entries.append(dict(source=str(src),target=str(dst),sha256=sha(src),before=sha(dst) if old else None,
            mode=mode,owner=who,old_mode=stat.S_IMODE(old.st_mode) if old else None,
            old_uid=old.st_uid if old else None,old_gid=old.st_gid if old else None))
    def generated(name, content):
        p = out/name; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(content,encoding='utf-8'); return p
    def public_file(src, relative, immutable=False):
        add(src, public/relative, 'www-data:www-data', immutable=immutable)
        add(src, site/relative, owner+':'+owner, immutable=immutable)
    portal = generated('sfdev.fé',page(app.read_text(),v))
    add(portal,app,'sfdev:sfdev',0o755); add(portal,site/'sfdev.fé',owner+':'+owner)
    manual = generated('manual.html',cache((source/'docs/manual.html').read_text(),v['nucleo']))
    add(manual, public/'manual/index.html','www-data:www-data')
    add(manual,site/'manual.html',owner+':'+owner)
    add(source/'docs/validar-manual.py',site/'validar-manual.py',owner+':'+owner)
    for rel in ('wasm/index.html','wasm/IDE/index.html'):
        if (public/rel).is_file():
            new = generated(rel.replace('/','-'),cache((public/rel).read_text(),v['nucleo']))
            add(new,public/rel,'www-data:www-data')
            if rel=='wasm/index.html': add(new,site/'wasm-index.html',owner+':'+owner)
    for name in ('santafe.js','santafe.wasm'):
        add(source/'src'/name,public/'wasm'/v['nucleo']/name,'www-data:www-data',immutable=True)
    for name in ('santafé','santafec','santafé-sls'):
        add(prefix/'bin'/name,system/'bin'/name,mode=0o755)
    for name in ('lua.h','luaconf.h','lauxlib.h','lualib.h','lua.hpp'):
        add(prefix/'include'/name,system/'include'/name)
    add(prefix/'lib/liblua.a',system/'lib/liblua.a')
    pc_text=(prefix/'lib/pkgconfig/santafe.pc').read_text()
    if pc_text.count('prefix='+str(prefix)+'\n')!=1 or 'Version: '+v['nucleo']+'\n' not in pc_text:
        raise ValueError('Prefixo/versão pkg-config divergente')
    add(generated('santafe.pc',pc_text.replace('prefix='+str(prefix)+'\n','prefix='+str(system)+'\n',1)),system/'lib/pkgconfig/santafe.pc')
    # Atualiza apenas ferramentas privadas. Não toca bibliotecas operacionais,
    # configurações, bancos, filas nem serviços de empresas usuárias.
    tools=Path('share/santafé/1.0/ferramentas')
    add(prefix/tools/'sls.fé',system/tools/'sls.fé')
    for name in ('analisador.fé','projetos.fé','semantica.fé','transporte.fé','api-publica.json','nativo.so'):
        add(prefix/tools/'sls'/name,system/tools/'sls'/name)
    for name in ('versoes','resolvedor','formatos','cliente','administracao','ambiente','cli','nativo'):
        file=name+('.so' if name=='nativo' else '.fé')
        add(prefix/tools/'pacotes'/file,system/tools/'pacotes'/file)
    hashes={}
    for extension in ('tar.gz','zip'):
        name='santafe-'+v['nucleo']+'.'+extension
        hashes[name]=sha(downloads/name); public_file(downloads/name,'baixar/'+name,True)
    vs,su,pc=validate_editors(source,v)
    for artifact,name in ((vs,'santafe-vscode-'+v['vscode']+'.vsix'),(su,'Santafe.sublime-package')):
        hashes[name]=sha(artifact); public_file(artifact,'baixar/'+name,name!='Santafe.sublime-package')
    public_file(pc,'sublime/'+pc.name,True)
    catalog={"schema_version":"4.0.0","packages":[{"name":"Santafe","description":"Linguagem Santafé e SLS","author":"Rafael Alves Lemos",
        "homepage":"https://xn--santaf-gva.dev.br/","labels":["language syntax"],"releases":[{"version":v['sublime'],"sublime_text":">=4107","platforms":["*"],
        "url":"https://xn--santaf-gva.dev.br/est%C3%A1tico/sublime/"+pc.name,"sha256":sha(pc),"date":"2026-10-21 00:00:00"}]}]}
    public_file(generated('packages.json',json.dumps(catalog,ensure_ascii=False,indent=2)+'\n'),'sublime/packages.json')
    public_file(generated('SHA256SUMS',editor.atualize_somas((public/'baixar/SHA256SUMS').read_text(),hashes)),'baixar/SHA256SUMS')
    index=json.loads((registry/'indice.json').read_text())
    prior_index=public/'bibliotecas/v1/indice.json'
    if prior_index.exists():
        prior=json.loads(prior_index.read_text())
        for name,old_versions in prior['pacotes'].items():
            for version,entry in old_versions.items():
                if index['pacotes'].get(name,{}).get(version)!=entry:
                    raise ValueError('Catálogo novo retiraria/alteraria versão publicada: '+name+'@'+version)
    allowed={'indice.json','index.html','SHA256SUMS'} | {e['arquivo'] for vers in index['pacotes'].values() for e in vers.values()}
    for name in allowed:
        path=Path(name)
        if path.is_absolute() or '..' in path.parts or str(path)!=name:
            raise ValueError('Caminho inseguro no catálogo')
        if (registry/path).is_symlink():
            raise ValueError('Link inseguro no catálogo')
        for parent in path.parents:
            if (registry/parent).is_symlink():
                raise ValueError('Diretório ligado no catálogo')
    for versions_ in index['pacotes'].values():
        for entry in versions_.values():
            if sha(registry/entry['arquivo'])!=entry['sha256']: raise ValueError('Catálogo adulterado')
    actual={p.relative_to(registry).as_posix() for p in registry.rglob('*') if p.is_file()}
    if actual!=allowed: raise ValueError('Arquivos extras/ausentes no catálogo')
    for name in sorted(allowed): public_file(registry/name,'bibliotecas/v1/'+name,name.endswith('.sfp'))
    for file in sorted(snapshot.rglob('*')):
        if file.is_file(): add(file,site.parent/'versoes'/v['nucleo']/file.relative_to(snapshot),owner+':'+owner,stat.S_IMODE(file.stat().st_mode),True)
    record={**v,'downloads':hashes,'source_tag':None,'intended_source_tag':'v'+v['nucleo'],
            'registry_index_sha256':sha(registry/'indice.json'),'restarted_services':['sfdev.service'],
            'persistent_services_not_restarted':True,'source':str(site.parent/'versoes'/v['nucleo'])}
    release=generated('release.json',json.dumps(record,ensure_ascii=False,indent=2)+'\n')
    public_file(release,'baixar/santafe-'+v['nucleo']+'.json',True)
    add(release,site.parent/'VERSAO-PUBLICADA.json',owner+':'+owner)
    if len({e['target'] for e in entries})!=len(entries): raise ValueError('Destinos duplicados')
    generated('plan.json',json.dumps(entries,ensure_ascii=False,indent=2)+'\n')
    print('Plano conjunto preparado, nenhum arquivo operacional alterado: '+str(len(entries)))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('prepare','install','verify','rollback'))
    for key in ('source','snapshot','prefix','downloads','registry','system','site','public','app','out','plan','backup'):
        p.add_argument('--'+key,type=Path)
    args=p.parse_args()
    if args.action=='prepare':
        prepare(*[getattr(args,key) for key in ('source','snapshot','prefix','downloads','registry','system','site','public','app','out')])
    elif args.action=='install':
        transaction.install(args.plan,args.backup)
    elif args.action=='verify': transaction.verify(args.plan)
    else: transaction.rollback(args.backup)
