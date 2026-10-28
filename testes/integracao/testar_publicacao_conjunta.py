#!/usr/bin/env python3
"""Preparo/instalação/rollback em diretórios descartáveis; sem sudo ou rede."""
import grp
import importlib.util
import json
import os
from pathlib import Path
import pwd
import shutil
import tempfile

ROOT=Path(__file__).resolve().parents[2]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
m=load('conjunto',ROOT/'operação/preparar-conjunto.py')
cat=load('curadoria',ROOT/'operação/preparar-catalogo-bibliotecas.py')
def rejects(fn):
    try: fn()
    except ValueError: return
    raise AssertionError('alteração insegura aceita')
def write(p,text):
    p.parent.mkdir(parents=True,exist_ok=True); p.write_text(text)
page='''-- preservar fora da rota: 2.0.3
ap.rota("GET", "/baixar", função(req, res)
local html=[[<h5>Santafé 2.0.3</h5>
santafe-2.0.3.tar.gz santafe-2.0.3.zip
<p>Extensão oficial 1.0.6: conteúdo anterior</p>
santafe-vscode-1.0.6.vsix santafe-vscode-1.0.6.vsix
<p>Pacote oficial 1.0.13 para arquivos .fé</p>
Santafe.sublime-package?v=1.0.13
      <h5 style="margin-top:32px">Instalação</h5>
]]
fim)
ap.rota("GET", "/outra", função(req,res)
-- preservar fora da rota: 2.0.3
fim)
'''
v=m.versions(ROOT)
converted=m.page(page,v)
assert converted.count('preservar fora da rota: 2.0.3')==2
assert m.page(converted,v)==converted
rejects(lambda:m.page(page.replace('Santafé 2.0.3','Santafé 9.9.9'),v))
rejects(lambda:m.page(page.replace('santafe-vscode-1.0.6.vsix','ausente'),v))

with tempfile.TemporaryDirectory(prefix='santafe-publicacao-conjunta-') as temporary:
    root=Path(temporary).resolve()
    source,snapshot,prefix,downloads,registry,system,site,public,out=[root/x for x in ('source','snapshot','prefix','downloads','registry','system','site','public','out')]
    # Use real editor artifacts; all operational paths are fixtures.
    source.mkdir(); (source/'extensões').mkdir()
    for name in ('vscode','sublime'):
        shutil.copytree(ROOT/'extensões'/name,source/'extensões'/name,ignore=shutil.ignore_patterns('__pycache__'))
    write(source/'operação/conjunto-versoes.json',json.dumps(v))
    for rel in ('src/santafe.js','src/santafe.wasm','docs/manual.html','docs/validar-manual.py'):
        write(source/rel,'fixture')
    write(snapshot/'README.md','fonte exato')
    for name in ('santafé','santafec','santafé-sls'): write(prefix/'bin'/name,'fixture')
    for name in ('lua.h','luaconf.h','lauxlib.h','lualib.h','lua.hpp'): write(prefix/'include'/name,'fixture')
    write(prefix/'lib/liblua.a','fixture')
    write(prefix/'lib/pkgconfig/santafe.pc','prefix='+str(prefix)+'\nVersion: '+v['nucleo']+'\n')
    tools=Path('share/santafé/3.0/ferramentas')
    write(prefix/tools/'sls.fé','fixture')
    for name in ('analisador.fé','projetos.fé','semantica.fé','transporte.fé','api-publica.json','nativo.so'): write(prefix/tools/'sls'/name,'fixture')
    for name in ('versoes','resolvedor','formatos','cliente','administracao','ambiente','cli','nativo'): write(prefix/tools/'pacotes'/(name+('.so' if name=='nativo' else '.fé')),'fixture')
    for ext in ('tar.gz','zip'): write(downloads/('santafe-'+v['nucleo']+'.'+ext),'fixture')
    cat.build(ROOT,ROOT/'src/santafé',registry)
    app=root/'app.fé'; write(app,page); write(site/'sfdev.fé',page)
    write(public/'baixar/SHA256SUMS','0'*64+'  santafe-2.0.3.tar.gz\n')
    old=public/'baixar/santafe-2.0.3.tar.gz'; write(old,'histórico')
    enterprise=system/'share/santafé/3.0/bibf/correio.fé'; write(enterprise,'não alterar')
    m.prepare(source,snapshot,prefix,downloads,registry,system,site,public,app,out)
    plan=out/'plan.json'; entries=json.loads(plan.read_text())
    assert app.read_text()==page and old.read_text()=='histórico'
    assert all('/bibf/' not in e['target'] for e in entries)
    assert any(e['target'].endswith('/pacotes/nativo.so') for e in entries)
    assert any(e['target'].endswith('/sls/semantica.fé') for e in entries)
    who=pwd.getpwuid(os.getuid()).pw_name+':'+grp.getgrgid(os.getgid()).gr_name
    for e in entries: e['owner']=who
    plan.write_text(json.dumps(entries))
    m.transaction.install(plan,root/'backup'); m.transaction.verify(plan)
    assert enterprise.read_text()=='não alterar' and old.read_text()=='histórico'
    assert (public/'bibliotecas/v1/indice.json').read_bytes()==(registry/'indice.json').read_bytes()
    m.transaction.rollback(root/'backup')
    assert app.read_text()==page and not (public/'bibliotecas/v1/indice.json').exists()
    original=m.transaction.atomic_copy; calls=[0]
    def fail(*args):
        calls[0]+=1
        if calls[0]==12: raise OSError('falha simulada')
        original(*args)
    m.transaction.atomic_copy=fail
    try:
        m.transaction.install(plan,root/'partial')
        raise AssertionError('falha não exercitada')
    except OSError: pass
    finally: m.transaction.atomic_copy=original
    m.transaction.rollback(root/'partial'); assert app.read_text()==page
    app.write_text(page+'-- edição concorrente')
    rejects(lambda:m.transaction.install(plan,root/'concurrent'))
    assert app.read_text().endswith('-- edição concorrente')
    app.write_text(page)
    changed=json.loads((registry/'indice.json').read_text())
    changed['pacotes']['semver']['1.0.0']['sha256']='0'*64
    write(public/'bibliotecas/v1/indice.json',json.dumps(changed))
    rejects(lambda:m.prepare(source,snapshot,prefix,downloads,registry,system,site,public,app,root/'bad'))
    print('Publicação conjunta: escopo, ferramentas completas, versões, catálogo, imutabilidade e rollback parcial: ok')
