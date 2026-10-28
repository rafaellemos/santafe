#!/usr/bin/env python3
"""Sela somente candidato de homologação; não aprova uma emissão pública não feita."""
from pathlib import Path
import hashlib,json,tarfile,zipfile,sys
p=Path(sys.argv[1]).resolve();base=p.parent/'candidato-dados-v14'
def need(v,s):
 if not v:raise SystemExit(s)
def sha(b):return hashlib.sha256(b).hexdigest()
def read(f):return json.loads(f.read_text())
need(p.name=='candidato-dados-v15' and p.parent.name=='dist' and not(p/'SHA256SUMS').exists(),'destino inválido ou já selado')
with tarfile.open(p/'santafe-candidato-dados.15-fontes.tar.gz') as t:
 ms=t.getmembers();need(all(x.isfile() and not Path(x.name).is_absolute() and '..' not in Path(x.name).parts for x in ms),'arquivo inseguro')
 manifest=json.load(t.extractfile('MANIFESTO-FONTES.json'));need(set(manifest)|{'MANIFESTO-FONTES.json'}=={x.name for x in ms} and len(ms)==len(manifest)+1,'manifesto')
 for n,h in manifest.items():need(sha(t.extractfile(n).read())==h,n)
 need(b'"dados.15"' in t.extractfile('src/lua.h').read(),'versão')
 delta=json.load(t.extractfile('DELTA-DADOS15.json'));need(delta['base_sha256']=='ddca28b7e058795ab5ff5d15a412ee8517962d421279df3bee20812cca47e5ce','base')
 labels=json.loads(t.extractfile('experimentos/dados-v13/rotulos-publicos.json').read().decode().replace('0.0.13','0.0.15'))
 for source,dest in [('docs/manual.html','manual.html')]+[('experimentos/dados-v15/'+n,n) for n in ['ESTADO.json','LEIA-ME.md','RELATORIO.md','acme-publico.py']]:need(t.extractfile(source).read()==(p/dest).read_bytes(),'documentação/roteiro diverge')
for system in ['macos','debian']:
 e=p/'evidencias'/system
 for n,c in [('dados10-regressao.json',10),('dados7-regressao.json',11)]:
  x=read(e/n);need(len(x)==c and [q['teste'] for q in x]==labels[n] and all(q['codigo']==0 for q in x),system+n)
 for n,c in [('iba10.json',14),('instalacao5.json',5)]:
  x=read(e/n);need(x['passaram']==labels[n] and x['esperados']==c,system+n)
 x=read(e/'operacao6.json');need(x['resultado']=='PASSOU' and [q['teste'] for q in x['testes']]==labels['operacao6.json'],system+' reversão')
 need(read(e/('pacotes-'+system+'.json'))['resultado']=='PASSOU',system+' pacotes')
 x=read(e/'auxiliar15.json');need(x['resultado']=='PASSOU' and len(x['grupos'])==12 and x['esperados']==12 and not x['rede_publica'],system+' auxiliar')
x=read(p/'evidencias/debian/acme-local15.json');need(x['resultado']=='PASSOU' and len(x['grupos'])==3 and not x['rede_externa'],'ACME local')
need(read(p/'evidencias/debian/wasm.json')['marcador']=='18 casos + recuperação após erro: ok','wasm')
mac=read(p/'evidencias/macos/kits15.json');need(mac==read(p/'evidencias/debian/kits15.json'),'kits')
for n,entries in mac.items():
 with zipfile.ZipFile(p/'editores'/n) as z:
  need(sorted(z.namelist())==sorted(entries),'kit incompleto')
  for f,h in entries.items():need(sha(z.read(f))==h,'kit divergente')
bins=read(p/'evidencias/debian/binarios15.json')
for n in ['santafe.js','santafe.wasm']:need(sha((p/'wasm'/n).read_bytes())==bins['src/'+n],'WASM divergente')
base_sums=dict((n,h) for h,n in (l.split('  ',1) for l in (base/'SHA256SUMS').read_text().splitlines()))
for n in ['conjunto14.json','carga14.json','imagens-reversao14.json','producao14.json']:
 src='evidencias/debian/'+n;need(sha((p/'evidencias/herdada-dados14'/n).read_bytes())==base_sums[src],'evidência herdada alterada')
x=read(p/'ESTADO.json');need(x['apto_para_homologacao'] and not x['apto_para_promocao_estavel'] and not x['producao_instalada'] and not x['producao_alterada'],'estado')
need(x['acme_publico']['estado']=='aguarda_execucao_com_sudo','emissão pública exige nova revisão da evidência')
need({q['codigo'] for q in x['pendencias']}=={'ACME_PUBLICO','PLATAFORMAS'},'pendências omitidas')
x=read(p/'evidencias/debian/producao15.json');need(x['resultado']=='PASSOU' and x['versao']=='2.1.0' and x['servicos_ativos']==7 and x['nucleo_e_processos_inalterados'],'produção')
files=sorted(x for x in p.rglob('*') if x.is_file());need(not any(x.is_symlink() for x in files),'link')
(p/'SHA256SUMS').write_text(''.join(sha(x.read_bytes())+'  '+str(x.relative_to(p))+'\n' for x in files))
print('DADOS15_SELADO',len(files),'arquivos; emissão pública ainda pendente')
