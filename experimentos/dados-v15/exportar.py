#!/usr/bin/env python3
"""Exporta somente rótulos conhecidos, contagens e hashes; nunca registros privados."""
from pathlib import Path
import argparse,hashlib,json,math,re,zipfile
R=Path(__file__).resolve().parents[2];E=R/'evidencias'
p=argparse.ArgumentParser();p.add_argument('--sistema',choices=['macos','debian'],required=True);p.add_argument('destino',type=Path);a=p.parse_args()
labels=json.loads((R/'experimentos/dados-v13/rotulos-publicos.json').read_text().replace('0.0.13','0.0.15'));out={};origins={}
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
 b=(Path('/tmp')/('dados15-'+name+'.log')).read_bytes();assert b.decode().strip().endswith(marker)
 out[name+'.json']={'resultado':'PASSOU','marcador':marker,'sha256':sha(b)}
bins=['src/santafé','src/santafec','ferramentas/sls/nativo.so','ferramentas/pacotes/nativo.so']+[f'bibs/bibc/{n}/{n}.so' for n in ['arquivo','rede','mariadb','segredo','tomada']]
if a.sistema=='debian':bins+=['src/santafe.js','src/santafe.wasm']
out['binarios15.json']={n:sha((R/n).read_bytes()) for n in bins}
kits={}
for name,entries in labels['kits'].items():
 with zipfile.ZipFile(R/'dist/candidato-dados-v15/editores'/name) as z:
  assert sorted(z.namelist())==entries and len(entries)==len(set(entries))
  kits[name]={n:sha(z.read(n)) for n in entries}
out['kits15.json']=kits
a.destino.write_text(json.dumps({'sanitizado':True,'sistema':a.sistema,'arquivos':out,'origens_sha256':origins},ensure_ascii=False,indent=2)+'\n')
print('EXPORTACAO15_OK',len(out))
