"""Lock de DLLs e fontes correspondentes; nenhum fonte é executado."""
from pathlib import Path, PurePosixPath
import hashlib,json,os,re,shutil,subprocess,urllib.request,urllib.parse
HERE=Path(__file__).resolve().parent
DIRECTORY='FONTES-TERCEIROS'
def sha(data):return hashlib.sha256(data).hexdigest()
def load_lock():
 lock=json.loads((HERE/'DEPENDENCIAS.lock.json').read_text(encoding='utf-8'))
 entries=lock['binarios'];names=[x['arquivo'] for x in entries]
 if len(entries)!=4 or len(set(names))!=4:raise ValueError('Lock incompleto ou duplicado')
 for e in entries:
  if not re.fullmatch(r'bin/[a-zA-Z0-9_.+-]+\.dll',e['arquivo']):raise ValueError('Caminho da DLL recusado')
  if not e['identidade'].startswith(e['pacote']+' '):raise ValueError('Dono incoerente')
  for k in ('fonte','assinatura'):
   a=e[k]
   if a['url']!='https://repo.msys2.org/mingw/sources/'+a['arquivo'] or '/' in a['arquivo'] or not re.fullmatch(r'[a-zA-Z0-9_.+-]+',a['arquivo']):raise ValueError('Origem de fonte recusada')
   if not re.fullmatch(r'[0-9a-f]{64}',a['sha256']) or not 0<a['bytes']<=40_000_000:raise ValueError('Limite inválido')
  for n in e['conteudos']:
   p=PurePosixPath(n)
   if p.is_absolute() or '..' in p.parts or '\\' in n or ':' in n or len(p.parts)!=2:raise ValueError('Membro de fonte recusado')
 return lock

def verify_data(data,entry):
 if len(data)!=entry['bytes'] or sha(data)!=entry['sha256']:raise ValueError('Fonte ou assinatura divergente: '+entry['arquivo'])

class OfficialRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  u=urllib.parse.urlsplit(newurl)
  if u.scheme!='https' or u.hostname!='repo.msys2.org' or u.username or u.password:raise ValueError('Redirecionamento recusado')
  return super().redirect_request(req,fp,code,msg,headers,newurl)

def fetch(entry,cache):
 path=cache/entry['arquivo']
 if path.is_symlink():raise ValueError('Vínculo recusado')
 if path.exists():verify_data(path.read_bytes(),entry);return path
 op=urllib.request.build_opener(OfficialRedirect())
 with op.open(entry['url'],timeout=40) as r:
  data=r.read(entry['bytes']+1)
 verify_data(data,entry)
 path.write_bytes(data)
 return path

def verify_source(path,entry):
 verify_data(path.read_bytes(),entry['fonte'])
 names=subprocess.check_output(['tar','-tf',str(path)],text=True,timeout=30).splitlines()
 files=[n for n in names if not n.endswith('/')]
 if len(names)!=len(set(names)) or set(files)!=set(entry['conteudos']):raise ValueError('Conteúdo do fonte divergente')
 for n in files:
  data=subprocess.check_output(['tar','-xOf',str(path),n],timeout=30)
  if sha(data)!=entry['conteudos'][n]:raise ValueError('Fonte interno divergente: '+n)
  if n.endswith('/.SRCINFO'):
   text=data.decode('utf-8')
   v=entry['identidade'].split(' ',1)[1].rsplit('-',1)
   if not all(re.search(r'^\s*'+k+r' = '+re.escape(val)+r'\s*$',text,re.M) for k,val in [('pkgver',v[0]),('pkgrel',v[1]),('pkgname',entry['pacote'])]):raise ValueError('Versão/família do fonte divergente')
 return len(files)

def verify_runtime(read,metadata,lock):
 byname={x['arquivo']:x for x in metadata['binarios']}
 if len(byname)!=len(metadata['binarios']) or set(byname)!={x['arquivo'] for x in lock['binarios']}:raise ValueError('Conjunto de DLLs divergente')
 for expected in lock['binarios']:
  e=byname[expected['arquivo']]
  if any(e[k]!=expected[k] for k in ('sha256','pacote','identidade')):raise ValueError('Dependência não homologada: '+expected['arquivo'])
  if sha(read(e['arquivo']))!=expected['sha256']:raise ValueError('DLL alterada: '+e['arquivo'])
 return len(byname)

def verify_signature(signature,source):
 # Native Windows Python cannot execute pacman-key (a shell script) itself.
 # Use bash/cygpath from the same MSYS2 installation as the verified package DB.
 pacman=shutil.which('pacman')
 if not pacman:raise ValueError('pacman ausente')
 bindir=Path(pacman).resolve().parent
 suffix='.exe' if os.name=='nt' else ''
 bash=bindir/('bash'+suffix);key=bindir/'pacman-key'
 if not bash.is_file() or not key.is_file():raise ValueError('Verificador MSYS2 incompleto')
 paths=[key,signature.resolve(),source.resolve()]
 if os.name=='nt':
  cygpath=bindir/'cygpath.exe'
  if not cygpath.is_file():raise ValueError('Conversor de caminhos MSYS2 ausente')
  args=[subprocess.check_output([str(cygpath),'-u',str(p)],text=True,timeout=10).strip() for p in paths]
 else:args=[str(p) for p in paths]
 return subprocess.run([str(bash),'--noprofile','--norc',args[0],'--verify',args[1],args[2]],capture_output=True,timeout=45)

def prepare(destination):
 lock=load_lock();metadata=json.loads((destination/'DEPENDENCIAS-MSYS2.json').read_text(encoding='utf-8'))
 verify_runtime(lambda n:(destination/n).read_bytes(),metadata,lock)
 target=destination/DIRECTORY;target.mkdir()
 cache=HERE/'cache-fontes';cache.mkdir(exist_ok=True)
 evidence=[]
 for e in lock['binarios']:
  source=fetch(e['fonte'],cache);sig=fetch(e['assinatura'],cache)
  p=verify_signature(sig,source)
  if p.returncode:raise ValueError('Assinatura MSYS2 recusada: '+e['fonte']['arquivo']+' '+p.stderr.decode('utf-8','replace')[-1000:])
  count=verify_source(source,e)
  for path in (source,sig):shutil.copyfile(path,target/path.name)
  evidence.append({'arquivo':source.name,'sha256':sha(source.read_bytes()),'membros_conferidos':count,'assinatura_msys2_verificada':True,'verificador':'pacman-key --verify','resultado_publico':(p.stdout+p.stderr).decode('utf-8','replace')})
 shutil.copyfile(HERE/'DEPENDENCIAS.lock.json',target/'DEPENDENCIAS.lock.json')
 shutil.copyfile(HERE/'FONTES-TERCEIROS.md',target/'LEIA-ME.md')
 (target/'VERIFICACAO.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 metadata.update(resolucao_runtime_fixada=True,resolucao_fixada=False,fontes_correspondentes_incluidas=True,observacao='Quatro DLLs com versão/hash fixos e respectivos fontes completos MSYS2 incluídos. Toolchain completo ainda não fixado; não atesta reprodução byte a byte.')
 (destination/'DEPENDENCIAS-MSYS2.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 # Keep the complete tool inventory as evidence, without copying unrelated licenses into the runtime.
 inventory=subprocess.check_output(['pacman','-Q'],text=True)
 (target/'AMBIENTE-CONSTRUCAO.txt').write_text(inventory,encoding='utf-8')
 return evidence

def verify_package(read):
 lock=load_lock()
 if json.loads(read(DIRECTORY+'/DEPENDENCIAS.lock.json'))!=lock:raise ValueError('Lock do pacote divergente')
 metadata=json.loads(read('DEPENDENCIAS-MSYS2.json'))
 verify_runtime(read,metadata,lock)
 for e in lock['binarios']:
  for k in ('fonte','assinatura'):verify_data(read(DIRECTORY+'/'+e[k]['arquivo']),e[k])
 proof=json.loads(read(DIRECTORY+'/VERIFICACAO.json'))
 if {x['arquivo'] for x in proof}!={e['fonte']['arquivo'] for e in lock['binarios']} or len(proof)!=4 or not all(x['assinatura_msys2_verificada'] for x in proof):raise ValueError('Verificação de fontes incompleta')
 if not metadata.get('fontes_correspondentes_incluidas') or not metadata.get('resolucao_runtime_fixada'):raise ValueError('Metadados incompletos')
 return 4
