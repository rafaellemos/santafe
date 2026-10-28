#!/usr/bin/env python3
"""Exportação por esquema fechado: contagens, rótulos fixos e hashes somente."""
from pathlib import Path
import argparse,hashlib,json,math,re,zipfile
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidencias'
p=argparse.ArgumentParser();p.add_argument('--sistema',choices=['macos','debian'],required=True);p.add_argument('destino',type=Path);a=p.parse_args()
labels=json.loads(Path(__file__).with_name('rotulos-publicos.json').read_text());out={};origins={}
def sha(b):return hashlib.sha256(b).hexdigest()
def read(n):
 b=(E/n).read_bytes();origins[n]=sha(b);return json.loads(b)
def num(v):
 assert type(v) in (int,float) and math.isfinite(v) and 0<=v<10**16
 return v
def h(v):assert re.fullmatch('[0-9a-f]{64}',v);return v
for n,count in [('dados10-regressao.json',10),('dados7-regressao.json',11)]:
 r=read(n);assert len(r)==count and [x['teste'] for x in r]==labels[n] and all(x['codigo']==0 for x in r)
 out[n]=[{'teste':label,'codigo':0,'segundos':num(x['segundos'])} for label,x in zip(labels[n],r)]
for n,count in [('iba10.json',14),('instalacao5.json',5)]:
 r=read(n);assert r['passaram']==labels[n] and r['esperados']==count
 out[n]={'passaram':labels[n],'esperados':count}
r=read('operacao6.json');assert r['resultado']=='PASSOU' and [x['teste'] for x in r['testes']]==labels['operacao6.json']
out['operacao6.json']={'resultado':'PASSOU','testes':[{'teste':x} for x in labels['operacao6.json']]}
markers={'pacotes13.log':('dados13-pacotes-'+a.sistema+'.log','ok'),'estrutura13.log':(None,'ESTRUTURA_UPLOAD_OK')}
if a.sistema=='debian':markers['wasm13.log']=('dados13-wasm-r2.log','18 casos + recuperação após erro: ok')
for n,(source,marker) in markers.items():
 b=(Path('/tmp')/source if source else E/n).read_bytes();assert marker in b.decode()
 if n=='pacotes13.log':assert b.decode().strip().endswith(marker)
 out[n]='Resumo sanitizado: '+marker+'\nSHA-256: '+sha(b)+'\n';origins[n]=sha(b)
bins=['src/santafé','src/santafec','ferramentas/sls/nativo.so','ferramentas/pacotes/nativo.so']+[f'bibs/bibc/{x}/{x}.so' for x in ['arquivo','rede','mariadb','segredo','tomada']]
if a.sistema=='debian':bins+=['src/santafe.js','src/santafe.wasm']
out['binarios13.json']={n:sha((ROOT/n).read_bytes()) for n in bins}
kits={}
for name,names in labels['kits'].items():
 with zipfile.ZipFile(ROOT/'dist/candidato-dados-v13/editores'/name) as z:
  assert sorted(z.namelist())==names and len(set(names))==len(names)
  kits[name]={n:sha(z.read(n)) for n in names}
out['kits13.json']=kits
if a.sistema=='debian':
 for n in ['servicos13.json','acme13.json','migracao-portal13.json']:
  r=read(n);assert r['resultado']=='PASSOU' and r['grupos']==labels[n]
  result={'resultado':'PASSOU','grupos':labels[n]}
  if n=='servicos13.json':
   assert r['dados']=='sinteticos' and r['producao_alterada'] is False
   result.update(dados='sinteticos',producao_alterada=False,assinaturas_sha256=h(r['assinaturas_sha256']),portal_correcao={k:h(r['portal_correcao'][k]) for k in ['antes','depois']})
  if n=='acme13.json':
   assert r['rede_externa'] is False and r['certificados_publicos_alterados'] is False
   result.update(rede_externa=False,certificados_publicos_alterados=False,certificado_inicial_sha256=h(r['certificado_inicial_sha256']),certificado_renovado_sha256=h(r['certificado_renovado_sha256']))
   assert result['certificado_inicial_sha256']!=result['certificado_renovado_sha256']
  if n=='migracao-portal13.json':result.update(antes=h(r['antes']),depois=h(r['depois']),producao_alterada=False)
  out[n]=result
 for n in ['dkim13.json','dkim-expiradas13.json']:
  r=read(n);assert r['resultado'] in ['PASSOU','INCONCLUSIVO'] and not r['conteudo_exportado'] and not r['relogio_alterado'] and r['mensagens_enviadas']==0
  keys=['mensagens','assinaturas','assinaturas_expiradas','assinaturas_validade_atual','originais_passaram','adulteradas_recusadas','originais_falharam','temporarios','inconclusivos']
  out[n]={'resultado':r['resultado'],**{k:num(r[k]) for k in keys},'conteudo_exportado':False,'relogio_alterado':False,'mensagens_enviadas':0}
 r=read('rede-publica13.json');assert r['resultado']=='PASSOU' and r['nucleo_e_processos_inalterados'] and r['mensagens_enviadas']==0 and [x['grupo'] for x in r['grupos']]==labels['rede-publica13.json']
 out['rede-publica13.json']={'resultado':'PASSOU','grupos':labels['rede-publica13.json'],'nucleo_e_processos_inalterados':True,'mensagens_enviadas':0}
 r=read('producao13.json');expected={'resultado':'PASSOU','versao':'2.1.0','servicos_ativos':7,'http_200':4,'nucleo_e_processos_inalterados_durante_conferencia':True}
 assert r==expected;out['producao13.json']=expected
a.destino.write_text(json.dumps({'sanitizado':True,'sistema':a.sistema,'arquivos':out,'origens_sha256':origins},ensure_ascii=False,indent=2)+'\n')
print('EXPORTACAO13_OK',len(out))
