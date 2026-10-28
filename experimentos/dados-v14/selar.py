#!/usr/bin/env python3
"""Só sela o candidato de homologação depois de todas as evidências exigidas."""
from pathlib import Path
import hashlib,json,sys,tarfile,zipfile
p=Path(sys.argv[1]).resolve()
def need(v,s):
 if not v:raise SystemExit(s)
def sha(b):return hashlib.sha256(b).hexdigest()
def read(f):return json.loads(f.read_text())
need(p.name=='candidato-dados-v14' and p.parent.name=='dist','destino inválido')
need(not(p/'SHA256SUMS').exists(),'já selado; não sobrescrever')
with tarfile.open(p/'santafe-candidato-dados.14-fontes.tar.gz') as t:
 members=t.getmembers();names={x.name for x in members}
 need(len(names)==len(members) and all(x.isfile() and not Path(x.name).is_absolute() and '..' not in Path(x.name).parts for x in members),'arquivo inseguro')
 manifest=json.load(t.extractfile('MANIFESTO-FONTES.json'));need(set(manifest)|{'MANIFESTO-FONTES.json'}==names,'manifesto incompleto')
 for n,h in manifest.items():need(sha(t.extractfile(n).read())==h,'fonte divergente '+n)
 need(b'"dados.14"' in t.extractfile('src/lua.h').read(),'versão incorreta')
 delta=json.load(t.extractfile('DELTA-DADOS14.json'));need(delta['base_sha256']=='dfed0891450d6b0465c2c2db3fc9013029c948a385a17ae6c11885bb807ece52','base incorreta')
 labels=json.loads(t.extractfile('experimentos/dados-v13/rotulos-publicos.json').read().decode().replace('0.0.13','0.0.14'))
 groups=json.load(t.extractfile('experimentos/dados-v14/grupos.json'))
 imagegroups=json.load(t.extractfile('experimentos/dados-v14/grupos-imagens.json'))
 for n,dest in [('docs/manual.html','manual.html')]+[('experimentos/dados-v14/'+n,n) for n in ['ESTADO.json','RELATORIO.md','LEIA-ME.md']]:need(t.extractfile(n).read()==(p/dest).read_bytes(),'documentação diverge')
for system in ['macos','debian']:
 e=p/'evidencias'/system
 for n,c in [('dados10-regressao.json',10),('dados7-regressao.json',11)]:
  x=read(e/n);need(len(x)==c and [q['teste'] for q in x]==labels[n] and all(q['codigo']==0 for q in x),system+' regressão')
 for n,c in [('iba10.json',14),('instalacao5.json',5)]:
  x=read(e/n);need(x['passaram']==labels[n] and x['esperados']==c,system+' '+n)
 x=read(e/'operacao6.json');need(x['resultado']=='PASSOU' and [q['teste'] for q in x['testes']]==labels['operacao6.json'],system+' reversão')
 need(read(e/('pacotes-'+system+'.json'))['resultado']=='PASSOU',system+' pacotes')
mac=read(p/'evidencias/macos/kits14.json');deb=read(p/'evidencias/debian/kits14.json');need(mac==deb,'kits divergentes')
for name,entries in mac.items():
 with zipfile.ZipFile(p/'editores'/name) as z:
  need(sorted(z.namelist())==sorted(entries),'kit incompleto')
  for n,h in entries.items():need(sha(z.read(n))==h,'kit alterado')
e=p/'evidencias/debian'
x=read(e/'conjunto14.json');need(x['resultado']=='PASSOU' and x['producao_alterada'] is False and x['rede_externa'] is False and [q['grupo'] for q in x['grupos']]==groups and len(groups)==21,'conjunto incompleto')
x=read(e/'carga14.json');need(x['resultado']=='PASSOU' and x['segundos']>=3600 and x['amostras']>=700 and x['operacoes']>=36000 and x['disco_min_mib']>=2048 and x['rss_max_kib']<=1536*1024,'carga incompleta')
x=read(e/'imagens-reversao14.json');need(x['resultado']=='PASSOU' and x['producao_alterada'] is False and [q['grupo'] for q in x['grupos']]==imagegroups and len(imagegroups)==6,'leitura de imagens após reversão')
x=read(e/'producao14.json');need(x['resultado']=='PASSOU' and x['versao']=='2.1.0' and x['servicos_ativos']==7 and x['http_200']==4 and x['nucleo_e_processos_inalterados'],'produção')
need(read(e/'wasm.json')['marcador']=='18 casos + recuperação após erro: ok','WASM')
bins=read(e/'binarios14.json')
for n in ['santafe.js','santafe.wasm']:need(sha((p/'wasm'/n).read_bytes())==bins['src/'+n],'WASM divergente')
x=read(p/'evidencias/mailjet13-confirmacao.json');need(x['tentativas']==1 and x['smtp_codigo']==250 and x['estado_mailjet']=='sent' and x['confirmacao_visual_do_destinatario'].startswith('recebida; acentos corretos'),'confirmação Mailjet')
x=read(p/'ESTADO.json');need(x['apto_para_homologacao'] and not x['apto_para_promocao_estavel'] and not x['producao_instalada'] and not x['producao_alterada'],'estado não permite selagem')
need({q['codigo'] for q in x['pendencias']}=={'ACME_PUBLICO','PLATAFORMAS'},'limites omitidos')
need('Não instalar em produção' in (p/'LEIA-ME.md').read_text(),'restrição ausente')
files=sorted(q for q in p.rglob('*') if q.is_file());need(not any(q.is_symlink() for q in files),'link inesperado')
(p/'SHA256SUMS').write_text(''.join(sha(q.read_bytes())+'  '+str(q.relative_to(p))+'\n' for q in files))
print('DADOS14_SELADO',len(files),'arquivos')
