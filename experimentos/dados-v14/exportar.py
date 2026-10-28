#!/usr/bin/env python3
"""Exporta somente rótulos conhecidos, contagens e hashes; nunca registros privados."""
from pathlib import Path
import argparse,hashlib,json,math,re,zipfile
R=Path(__file__).resolve().parents[2];E=R/'evidencias'
p=argparse.ArgumentParser();p.add_argument('--sistema',choices=['macos','debian'],required=True);p.add_argument('--replica',type=Path);p.add_argument('destino',type=Path);a=p.parse_args()
labels=json.loads((R/'experimentos/dados-v13/rotulos-publicos.json').read_text().replace('0.0.13','0.0.14'));out={};origins={}
def sha(b):return hashlib.sha256(b).hexdigest()
def read(n):
 b=(E/n).read_bytes();origins[n]=sha(b);return json.loads(b)
def num(v):assert type(v) in (int,float) and math.isfinite(v) and 0<=v<10**16;return v
for n,c in [('dados10-regressao.json',10),('dados7-regressao.json',11)]:
 x=read(n);assert len(x)==c and [q['teste'] for q in x]==labels[n] and all(q['codigo']==0 for q in x)
 out[n]=[{'teste':l,'codigo':0,'segundos':num(q['segundos'])} for l,q in zip(labels[n],x)]
for n,c in [('iba10.json',14),('instalacao5.json',5)]:
 x=read(n);assert x['passaram']==labels[n] and x['esperados']==c
 out[n]={'passaram':labels[n],'esperados':c}
x=read('operacao6.json');assert x['resultado']=='PASSOU' and [q['teste'] for q in x['testes']]==labels['operacao6.json']
out['operacao6.json']={'resultado':'PASSOU','testes':[{'teste':l} for l in labels['operacao6.json']]}
for name,marker in [('pacotes-'+a.sistema,'ok')]+([('wasm','18 casos + recuperação após erro: ok')] if a.sistema=='debian' else []):
 b=(Path('/tmp')/('dados14-'+name+'.log')).read_bytes();assert b.decode().strip().endswith(marker)
 out[name+'.json']={'resultado':'PASSOU','marcador':marker,'sha256':sha(b)}
bins=['src/santafé','src/santafec','ferramentas/sls/nativo.so','ferramentas/pacotes/nativo.so']+[f'bibs/bibc/{n}/{n}.so' for n in ['arquivo','rede','mariadb','segredo','tomada']]
if a.sistema=='debian':bins+=['src/santafe.js','src/santafe.wasm']
out['binarios14.json']={n:sha((R/n).read_bytes()) for n in bins}
kits={}
for name,entries in labels['kits'].items():
 with zipfile.ZipFile(R/'dist/candidato-dados-v14/editores'/name) as z:
  assert sorted(z.namelist())==entries and len(entries)==len(set(entries))
  kits[name]={n:sha(z.read(n)) for n in entries}
out['kits14.json']=kits
if a.sistema=='debian':
 assert a.replica and a.replica.name.startswith('santafe-migracao11-') and a.replica.parent==Path('/var/tmp')
 b=(a.replica/'resultado-dados14.json').read_bytes();origins['conjunto14']=sha(b);x=json.loads(b)
 expected=json.loads(Path(__file__).with_name('grupos.json').read_text())
 assert x['resultado']=='PASSOU' and x['producao_alterada'] is False and [q['grupo'] for q in x['grupos']]==expected
 keys={'santafe_comunidade','paodocafe','iba','requisicoes','zonas','respostas_assinadas','originais','anexos','paginas','entrada_sem_destino_http','segundos','operacoes','clientes','p95_ms','rss_max_kib','disco_livre_min_mib'}
 groups=[]
 for label,q in zip(expected,x['grupos']):groups.append({'grupo':label,**{k:num(v) for k,v in q.items() if k in keys}})
 out['conjunto14.json']={'resultado':'PASSOU','producao_alterada':False,'rede_externa':False,'grupos':groups}
 b=(a.replica/'carga-dados14.json').read_bytes();origins['carga14']=sha(b);x=json.loads(b)
 assert x['resultado']=='PASSOU' and not x['falhas'] and x['segundos']>=3600 and x['limite_pedidos_por_segundo']==12 and len(x['contadores'])==6 and min(x['contadores'])>=6000
 samples=x['amostras'];assert len(samples)>=700
 assert all(q['livre_mib']>=2048 and q['rss_kib']<=1536*1024 and q['descritores']<=2048 and q['registros_bytes']<=128*1024**2 and q['memoria_disponivel_kib']>=768*1024 for q in samples)
 out['carga14.json']={'resultado':'PASSOU','segundos':num(x['segundos']),'operacoes':sum(map(num,x['contadores'])),'amostras':len(samples),'rss_max_kib':max(num(q['rss_kib']) for q in samples),'disco_min_mib':min(num(q['livre_mib']) for q in samples),'registros_max_bytes':max(num(q['registros_bytes']) for q in samples),'descritores_max':max(num(q['descritores']) for q in samples),'limite_pedidos_por_segundo':12}
 b=(a.replica/'imagens-reversao14.json').read_bytes();origins['imagens-reversao14']=sha(b);x=json.loads(b)
 expected=json.loads(Path(__file__).with_name('grupos-imagens.json').read_text())
 assert x['resultado']=='PASSOU' and [q['grupo'] for q in x['grupos']]==expected and x['producao_alterada'] is False
 out['imagens-reversao14.json']={'resultado':'PASSOU','producao_alterada':False,'grupos':[{'grupo':l,**{k:num(v) for k,v in q.items() if k in {'arquivos','novas','imagens'}}} for l,q in zip(expected,x['grupos'])]}
 x=read('producao14.json');assert x['resultado']=='PASSOU' and x['versao']=='2.1.0' and x['nucleo_e_processos_inalterados'] and x['servicos_ativos']==7 and x['http_200']==4
 out['producao14.json']={k:x[k] for k in ('resultado','versao','nucleo_e_processos_inalterados','servicos_ativos','http_200')}
a.destino.write_text(json.dumps({'sanitizado':True,'sistema':a.sistema,'arquivos':out,'origens_sha256':origins},ensure_ascii=False,indent=2)+'\n')
print('EXPORTACAO14_OK',len(out))
