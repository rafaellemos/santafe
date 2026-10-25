"""Checks positive controls and rejection of incomplete redistribution notices."""
from pathlib import Path
import hashlib,json,shutil,sys,tempfile,zipfile
from licencas import prepare,verify_tree,verify_archive,SOURCES,DIRECTORY
root=Path(sys.argv[1]).resolve();results=[]
def ok(name):results.append(name)
def refused(name,fn):
 try:fn()
 except (ValueError,FileNotFoundError,KeyError):ok(name)
 else:raise AssertionError('Falha não detectada: '+name)
with tempfile.TemporaryDirectory(prefix='santafe-licencas-') as td:
 out=Path(td);tree=out/'pacote';tree.mkdir();entries=prepare(root,tree)
 assert verify_tree(tree)==6;ok('seis-avisos-reais-preservados')
 for e in entries:
  assert e['fonte_sha256']==hashlib.sha256((root/e['fonte']).read_bytes()).hexdigest()
 ok('procedencia-fonte-compilado')
 def archive(name):
  files={p.relative_to(tree).as_posix():p.read_bytes() for p in tree.rglob('*') if p.is_file()}
  files['SHA256.json']=json.dumps({n:hashlib.sha256(b).hexdigest() for n,b in files.items()}).encode()
  dest=out/name
  with zipfile.ZipFile(dest,'w') as z:
   for n,b in files.items():z.writestr(n,b)
  return dest
 assert verify_archive(archive('correto.zip'))==6;ok('zip-com-avisos-e-integridade')
 for source,name,*rest in SOURCES:
  path=tree/DIRECTORY/name;data=path.read_bytes();path.unlink()
  refused('recusa-ausente-'+name,lambda:verify_archive(archive('ausente.zip')))
  path.write_bytes(data+b'corrompido')
  refused('recusa-corrompido-'+name,lambda:verify_archive(archive('corrompido.zip')))
  path.write_bytes(data)
 index=tree/DIRECTORY/'INDICE.json';valid=index.read_bytes();items=json.loads(valid)
 index.write_text(json.dumps(items+[items[0]]),encoding='utf-8')
 refused('recusa-aviso-duplicado',lambda:verify_tree(tree));index.write_bytes(valid)
 index.write_text(json.dumps(items[1:]),encoding='utf-8')
 refused('recusa-indice-incompleto',lambda:verify_tree(tree));index.write_bytes(valid)
 badroot=out/'fonte';badroot.mkdir()
 target=out/'sem-fonte';target.mkdir()
 refused('recusa-fonte-sem-aviso',lambda:prepare(badroot,target))
 # A recomputed ZIP checksum must not turn an empty licence into a valid notice.
 path=tree/DIRECTORY/items[0]['arquivo'];data=path.read_bytes();path.write_bytes(b'')
 items[0]['sha256']=hashlib.sha256(b'').hexdigest();index.write_text(json.dumps(items),encoding='utf-8')
 refused('recusa-aviso-vazio-com-hash-recalculado',lambda:verify_archive(archive('vazio.zip')))
 path.write_bytes(data);index.write_bytes(valid)
 output={'resultado':'passou_avisos_redistribuicao','testes':results,'total':len(results),'producao_alterada':False}
 print(json.dumps(output,ensure_ascii=False,indent=2))
 if len(sys.argv)>2:Path(sys.argv[2]).write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
