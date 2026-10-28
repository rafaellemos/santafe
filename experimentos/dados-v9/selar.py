#!/usr/bin/env python3
"""Confere fontes, kits e evidências antes de selar a entrega de laboratório."""
from pathlib import Path
import hashlib, json, sys, tarfile, zipfile

def require(ok, message):
    if not ok:
        raise SystemExit(message)

out = Path(sys.argv[1]).resolve()
require(out.name == 'candidato-dados-v9' and out.parent.name == 'dist', 'Destino inválido')
require(not (out/'SHA256SUMS').exists(), 'Entrega já selada; não sobrescrever')
archive = out/'santafe-candidato-dados.9-fontes.tar.gz'
with tarfile.open(archive) as pack:
    members = pack.getmembers()
    require(all(m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in members), 'Arquivo inseguro')
    require(len({m.name for m in members}) == len(members), 'Membros duplicados')
    manifest = json.load(pack.extractfile('MANIFESTO-FONTES.json'))
    require(set(manifest) | {'MANIFESTO-FONTES.json'} == {m.name for m in members}, 'Manifesto incompleto')
    for name, sha in manifest.items():
        require(hashlib.sha256(pack.extractfile(name).read()).hexdigest() == sha, 'Fonte divergente: '+name)
    require(b'"dados.9"' in pack.extractfile('src/lua.h').read(), 'Versão do núcleo')
    require(b'1.0.0-dados.9' in pack.extractfile('ferramentas/sls/sls.fé').read(), 'Versão SLS')
    require(pack.extractfile('docs/manual.html').read() == (out/'manual.html').read_bytes(), 'Manual diferente do ensaiado')

for platform in ('macos', 'debian'):
    ev = out/'evidencias'/platform
    for name, count in (('dados9-regressao.json', 10), ('dados7-regressao.json', 11)):
        tests = json.loads((ev/name).read_text())
        require(len(tests) == count and all(t['codigo'] == 0 for t in tests), platform+' '+name)
    require(len(json.loads((ev/'dados8-fontes.json').read_text())) == 183, platform+' fontes')
    require(len(json.loads((ev/'aplicativos5.json').read_text())['passaram']) == 13, platform+' aplicativos')
    require(len(json.loads((ev/'instalacao5.json').read_text())['passaram']) == 5, platform+' instalação')
    require(json.loads((ev/'onfe-persistencia7.json').read_text())['passou'], platform+' persistência')
    require(json.loads((ev/'operacao6.json').read_text())['resultado'] == 'PASSOU', platform+' operação')
    require(json.loads((ev/'carga6.json').read_text())['resultado'] == 'PASSOU', platform+' carga')
    log = (ev/'dados9-colares.log').read_text()
    require('Ran 14 tests' in log and '\nOK\n' in log, platform+' colares')
require('18 casos + recuperação após erro: ok' in (out/'evidencias/debian/dados9-wasm.log').read_text(), 'WASM não aprovado')
require((out/'wasm/santafe.wasm').read_bytes()[:4] == b'\0asm', 'WASM inválido')

ev = out/'evidencias/editores'
v = json.loads((ev/'vscode-dados9-resultado.json').read_text())
s = json.loads((ev/'sublime-dados9-resultado.json').read_text())
require(v['resultado'] == s['resultado'] == 'ok', 'Hosts não aprovados')
require(len(v['grupos']) == 8 and len(s['grupos']) == 6, 'Grupos incompletos')
require(v['extensão'] == '0.0.9' and v['sls']['version'] == '1.0.0-dados.9', 'Host usou outra versão')
require(all('source.santafe-dados9-host-' in scope for scope in s['escopos'].values()), 'Escopo Sublime incorreto')
visual = json.loads((ev/'inspecao-visual.json').read_text())
with zipfile.ZipFile(out/'editores/santafe-dados-experimental-0.0.9.vsix') as z:
    pkg = json.loads(z.read('extension/package.json'))
    require(pkg['version'] == '0.0.9' and pkg['name'] == 'santafe-dados-experimental', 'Kit VS Code incorreto')
    for name, sha in visual['kit_vscode'].items():
        require(hashlib.sha256(z.read('extension/'+name)).hexdigest() == sha, 'Kit difere do inspecionado: '+name)
    require(b'light:{fontStyle:fonte}, dark:{fontStyle:fonte}' in z.read('extension/aparencia.js'), 'Correção visual ausente')
with zipfile.ZipFile(out/'editores/SantafeDados.sublime-package') as z:
    require("- match: '\\[(=+)\\['" in z.read('Santafe-Dados.sublime-syntax').decode(), 'Delimitador Sublime incorreto')
    require(b'0.0.9' in z.read('README.md'), 'Versão Sublime incorreta')

files = sorted(p for p in out.rglob('*') if p.is_file())
require(not any(p.is_symlink() or '\n' in str(p) for p in files), 'Arquivo inválido')
require(all((out/n).is_file() for n in ('ENTREGA.md', 'RELATORIO.md', 'LEIA-ME.md')), 'Documentação incompleta')
(out/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(out))+'\n' for p in files))
print('DADOS9_SELADO', hashlib.sha256(archive.read_bytes()).hexdigest(), len(files), 'arquivos')
