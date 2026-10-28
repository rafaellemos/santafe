#!/usr/bin/env python3
"""Confere evidências executadas antes de selar o candidato; nunca publica."""
from pathlib import Path
import hashlib,json,sys,tarfile,zipfile
def require(ok,msg):
 if not ok:raise SystemExit(msg)
o=Path(sys.argv[1]).resolve()
require(o.name=='candidato-dados-v11' and o.parent.name=='dist','destino inválido')
require(not(o/'SHA256SUMS').exists(),'entrega já selada')
with tarfile.open(o/'santafe-candidato-dados.11-fontes.tar.gz') as p:
 members=p.getmembers();names={m.name for m in members}
 require(len(names)==len(members) and all(m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in members),'arquivo inseguro')
 manifest=json.load(p.extractfile('MANIFESTO-FONTES.json'))
 require(set(manifest)|{'MANIFESTO-FONTES.json'}==names,'manifesto incompleto')
 for n,h in manifest.items():require(hashlib.sha256(p.extractfile(n).read()).hexdigest()==h,'fonte divergente '+n)
 require(b'"dados.11"' in p.extractfile('src/lua.h').read(),'versão de núcleo')
 require(b'#define SANTAFE_ABI_MAJOR 3' in p.extractfile('src/lua.h').read(),'IBA')
 require(p.extractfile('docs/manual.html').read()==(o/'manual.html').read_bytes(),'manual divergente')
 for n in ('RELATORIO.md','ESTADO.json','LEIA-ME.md'):
  require(p.extractfile('experimentos/dados-v11/'+n).read()==(o/n).read_bytes(),'documento divergente '+n)
for system in ('macos','debian'):
 e=o/'evidencias'/system
 for n,c in (('dados10-regressao.json',10),('dados7-regressao.json',11)):
  r=json.loads((e/n).read_text());require(len(r)==c and all(x['codigo']==0 for x in r),system+' '+n)
 for n,c in (('iba10.json',14),('instalacao5.json',5)):
  r=json.loads((e/n).read_text());require(r['esperados']==c and len(r['passaram'])==c,system+' '+n)
 r=json.loads((e/'operacao6.json').read_text());require(r['resultado']=='PASSOU' and len(r['testes'])==7,system+' gerações')
 require('Pacotes: empacotamento determinístico' in (e/('dados11-pacotes-'+system+'.log')).read_text() and (e/('dados11-pacotes-'+system+'.log')).read_text().strip().endswith('ok'),system+' gerenciador')
 require(json.loads((e/'binarios11.json').read_text()),system+' binários não registrados')
e=o/'evidencias/debian'
r=json.loads((e/'replica11-sintetica.json').read_text());require(r['esperados']==len(r['passaram'])==10 and r['sintetico'],'restauração adversarial')
r=json.loads((e/'replica11-real.json').read_text());require(r['resultado']=='PASSOU' and r['sanitizado'] and len(r['grupos'])==23,'réplica incompleta')
load=[x for x in r['grupos'] if x['grupo']=='carga da réplica candidata'];require(len(load)==1 and load[0]['segundos']>=60 and load[0]['clientes']==6,'carga real')
read=[x for x in r['grupos'] if x['grupo']=='estavel: leitura dos aplicativos e conteúdo integral'];require(read[-1]['originais']==141 and read[-1]['anexos']==22,'escritas pós-migração')
require('18 casos + recuperação após erro: ok' in (e/'dados11-wasm.log').read_text(),'WASM')
require((o/'wasm/santafe.wasm').read_bytes()[:4]==b'\0asm','WASM inválido')
with zipfile.ZipFile(o/'editores/santafe-dados-experimental-0.0.11.vsix') as z:
 require(json.loads(z.read('extension/package.json'))['version']=='0.0.11','versão VS Code')
with zipfile.ZipFile(o/'editores/SantafeDados.sublime-package') as z:
 require(b'0.0.11' in z.read('README.md'),'versão Sublime')
state=json.loads((o/'ESTADO.json').read_text());require(state['apto_para_homologacao'] and not state['apto_para_promocao_estavel'] and not state['producao_alterada'],'estado incorreto')
require('HTTP503_CARGA_INTERMITENTE' in {p['codigo'] for p in state['pendencias']},'pendência omitida')
require('Não instalar em produção' in (o/'LEIA-ME.md').read_text(),'restrição ausente')
files=sorted(p for p in o.rglob('*') if p.is_file())
require(not any(p.is_symlink() or '\n' in str(p) for p in files),'membro inseguro')
(o/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(o))+'\n' for p in files))
print('DADOS11_SELADO',len(files),'arquivos; homologação, sem promoção estável')
