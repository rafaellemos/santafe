"""Adversarial redistribution checks; reads only the candidate ZIP."""
from pathlib import Path
import copy,json,sys,zipfile
from dependencias import verify_package,load_lock
with zipfile.ZipFile(sys.argv[1]) as z: files={n:z.read(n) for n in z.namelist()}
results=[]
def passed(name):results.append({'nome':name,'passou':True})
def refuse(name,change):
 sample=dict(files);change(sample)
 try:verify_package(sample.__getitem__)
 except (ValueError,KeyError,FileNotFoundError):passed(name);return
 raise AssertionError('Aceitou: '+name)
assert verify_package(files.__getitem__)==4;passed('fontes-completos-e-runtime-fixo')
for e in load_lock()['binarios']:
 name=e['arquivo']
 refuse('dll-alterada-'+name,lambda d,n=name:d.__setitem__(n,b'alterado'))
 for key in ('fonte','assinatura'):
  name='FONTES-TERCEIROS/'+e[key]['arquivo']
  refuse('ausente-'+name,lambda d,n=name:d.pop(n))
  refuse('alterado-'+name,lambda d,n=name:d.__setitem__(n,b'alterado'))
def metadata_change(d,field,value):
 meta=json.loads(d['DEPENDENCIAS-MSYS2.json']);meta['binarios'][0][field]=value;d['DEPENDENCIAS-MSYS2.json']=json.dumps(meta).encode()
for field,value in [('identidade','glib 999'),('pacote','outro'),('sha256','0'*64)]:
 refuse('metadado-'+field,lambda d,f=field,v=value:metadata_change(d,f,v))
def inventory(d,duplicate=False):
 meta=json.loads(d['DEPENDENCIAS-MSYS2.json'])
 if duplicate:meta['binarios'].append(meta['binarios'][0])
 else:meta['binarios'].pop()
 d['DEPENDENCIAS-MSYS2.json']=json.dumps(meta).encode()
refuse('dll-nao-inventariada',inventory)
refuse('dll-duplicada',lambda d:inventory(d,True))
refuse('lock-do-pacote-ausente',lambda d:d.pop('FONTES-TERCEIROS/DEPENDENCIAS.lock.json'))
def wronglock(d):
 lock=json.loads(d['FONTES-TERCEIROS/DEPENDENCIAS.lock.json']);lock['binarios'][0]['identidade']='nova';d['FONTES-TERCEIROS/DEPENDENCIAS.lock.json']=json.dumps(lock).encode()
refuse('lock-do-pacote-alterado',wronglock)
refuse('verificacao-ausente',lambda d:d.pop('FONTES-TERCEIROS/VERIFICACAO.json'))
def badproof(d):
 proof=json.loads(d['FONTES-TERCEIROS/VERIFICACAO.json']);proof[0]['assinatura_msys2_verificada']=False;d['FONTES-TERCEIROS/VERIFICACAO.json']=json.dumps(proof).encode()
refuse('assinatura-nao-verificada',badproof)
Path(sys.argv[2]).write_text(json.dumps({'resultado':'passou_fontes_e_dependencias','total':len(results),'testes':results,'producao_alterada':False},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('DEPENDENCIAS_ADVERSARIAIS_OK',len(results))
