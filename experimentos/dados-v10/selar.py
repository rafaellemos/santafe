#!/usr/bin/env python3
"""Sela apenas candidato de homologação; exige testes, declara migração pendente."""
from pathlib import Path
import hashlib,json,sys,tarfile,zipfile

def require(ok,msg):
 if not ok:raise SystemExit(msg)
o=Path(sys.argv[1]).resolve();require(o.name=='candidato-dados-v10' and o.parent.name=='dist','Destino inválido');require(not(o/'SHA256SUMS').exists(),'Já selado')
with tarfile.open(o/'santafe-candidato-dados.10-fontes.tar.gz') as pack:
 members=pack.getmembers();names={m.name for m in members}
 require(len(names)==len(members) and all(m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in members),'tar inseguro')
 m=json.load(pack.extractfile('MANIFESTO-FONTES.json'));require(set(m)|{'MANIFESTO-FONTES.json'}==names,'manifesto incompleto')
 for n,h in m.items():require(hashlib.sha256(pack.extractfile(n).read()).hexdigest()==h,'fonte divergente '+n)
 require(b'"dados.10"' in pack.extractfile('src/lua.h').read(),'versão')
 require(b'#define SANTAFE_ABI_MAJOR 3' in pack.extractfile('src/lua.h').read(),'IBA')
 require(b'#define LUA_SIGNATURE "\\x1bSF3"' in pack.extractfile('src/lua.h').read(),'bytecode')
 require(pack.extractfile('docs/manual.html').read()==(o/'manual.html').read_bytes(),'manual divergente')
for system in ('macos','debian'):
 ev=o/'evidencias'/system
 for name,count in (('dados10-regressao.json',10),('dados7-regressao.json',11)):
  r=json.loads((ev/name).read_text());require(len(r)==count and all(t['codigo']==0 for t in r),system+' '+name)
 for name,count in (('iba10.json',14),('aplicativos5.json',13),('instalacao5.json',5)):
  r=json.loads((ev/name).read_text());require(r['esperados']==count and len(r['passaram'])==count,system+' '+name)
 for name in ('carga6.json','operacao6.json'):
  require(json.loads((ev/name).read_text())['resultado']=='PASSOU',system+' '+name)
 require(json.loads((ev/'carga6.json').read_text())['segundos']>=60,system+' carga curta')
 require('Pacotes: empacotamento determinístico' in (ev/'dados10-pacotes.log').read_text() and (ev/'dados10-pacotes.log').read_text().strip().endswith('ok'),system+' pacotes')
r=json.loads((o/'evidencias/debian/replica10-sintetica.json').read_text());require(len(r['passaram'])==r['esperados']==10 and r['sintetico'] and not r['replica_real_validada'],'estado réplica')
require('18 casos + recuperação após erro: ok' in (o/'evidencias/debian/dados10-wasm.log').read_text(),'WASM')
require((o/'wasm/santafe.wasm').read_bytes()[:4]==b'\0asm','WASM inválido')
with zipfile.ZipFile(o/'editores/santafe-dados-experimental-0.0.10.vsix') as z:
 p=json.loads(z.read('extension/package.json'));require(p['version']=='0.0.10' and p['name']=='santafe-dados-experimental','kit VSCode')
 require(b'light:{fontStyle:fonte}, dark:{fontStyle:fonte}' in z.read('extension/aparencia.js'),'correção visual')
with zipfile.ZipFile(o/'editores/SantafeDados.sublime-package') as z:
 require(b'0.0.10' in z.read('README.md'),'kit Sublime')
 require("- match: '\\[(=+)\\['" in z.read('Santafe-Dados.sublime-syntax').decode(),'delimitadores Sublime')
require('RÉPLICA REAL PENDENTE' in (o/'RELATORIO.md').read_text(),'limite ausente')
state=json.loads((o/'ESTADO.json').read_text());require(not state['apto_para_promocao_estavel'] and not state['producao_alterada'],'estado incorreto')
require({'REPLICA_REAL','HTTP503_CARGA_INTERMITENTE'}.issubset({p['codigo'] for p in state['pendencias']}),'pendências omitidas')
require('não instalar em produção' in (o/'LEIA-ME.md').read_text(),'restrição ausente')
files=sorted(p for p in o.rglob('*') if p.is_file());require(not any(p.is_symlink() or '\n' in str(p) for p in files),'arquivo inseguro')
(o/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(o))+'\n' for p in files))
print('DADOS10_SELADO',len(files),'arquivos; candidato, não promoção estável')
