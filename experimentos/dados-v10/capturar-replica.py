#!/usr/bin/env python3
"""Cópia privada somente de leitura da instalação. Nunca para/reinicia serviços.
Dados/credenciais ficam no próprio servidor, sob modo 0700; não publicar o snapshot.
Não executar serviços a partir desta cópia: a adaptação de rede é etapa separada.
"""
from pathlib import Path
import argparse, hashlib, json, os, pwd, resource, shutil, stat, subprocess, tempfile, time
p=argparse.ArgumentParser();p.add_argument('--copiar-dados',action='store_true');a=p.parse_args()
if os.geteuid()!=0 or not a.copiar_dados:raise SystemExit('Use sudo python3 ... --copiar-dados para a réplica privada autorizada')
user=os.environ.get('SUDO_USER','')
if not user or user=='root':raise SystemExit('Execute sudo a partir da conta rafael; não deixa snapshot legível globalmente')
owner=pwd.getpwnam(user)
os.umask(0o077)
root=Path(tempfile.mkdtemp(prefix='santafe-replica-dados10-',dir='/var/tmp'))
(root/'.replica-privada').write_text('NÃO EXECUTAR: contém configuração/dados operacionais; adaptar ao isolamento antes de iniciar.\n')
files={};changes=[];copied=0
limit=8*1024**3
roots=['/usr/local/bin/santafé','/usr/local/bin/santafec','/usr/local/bin/santafé-sls',
 '/usr/local/share/santafé/1.0','/usr/local/lib/santafé/1.0',*[f'/usr/local/include/{n}' for n in ('lua.h','luaconf.h','lauxlib.h','lualib.h','lua.hpp')],
 *[str(x) for x in Path('/opt').glob('*.fé')],'/opt/carteiro','/opt/correio','/opt/santafe-nomes','/opt/santafe-dns','/opt/paodocafe',
 '/var/www/santafé.dev.br','/var/www/pãodocafé.com.br','/etc/santafe','/etc/paodocafe',
 '/etc/nginx','/etc/santafe-nomes','/etc/santafe-dns','/etc/santafe-correio','/var/lib/santafé/correio','/var/lib/paodocafe/correio']
def sha256(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def run(cmd):return subprocess.check_output(cmd,text=True,stderr=subprocess.PIPE,timeout=120)
def copyfile(src):
 global copied
 info=src.stat()
 if not stat.S_ISREG(info.st_mode):return
 if info.st_size+copied>limit or shutil.disk_usage(root).free<info.st_size+1024**3:raise RuntimeError('limite de cópia/espaço livre')
 relative=str(src).lstrip('/')
 if relative in files:return
 dst=root/'arquivos'/relative;dst.parent.mkdir(parents=True,exist_ok=True)
 with src.open('rb') as f, dst.open('xb') as g:
  before=os.fstat(f.fileno());h=hashlib.sha256()
  while True:
   b=f.read(1024*1024)
   if not b:break
   h.update(b);g.write(b)
  after=os.fstat(f.fileno())
 if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):changes.append(relative)
 copied+=info.st_size
 files[relative]={'sha256':h.hexdigest(),'modo':stat.S_IMODE(info.st_mode),'uid':info.st_uid,'gid':info.st_gid,'tamanho':info.st_size}
 # Never preserve execution permission on copied runtime/application files.
 os.chmod(dst,0o600)
try:
 names=[x.split()[0] for x in run(['systemctl','list-unit-files','--no-legend']).splitlines() if x.startswith(('sfdev.','correio-','carteiro','paodocafe.','nomes-','santafe-nomes','santafe-dns','sfdns'))]
 units={}
 for name in names:
  props=run(['systemctl','show',name,'--property=ActiveState,FragmentPath,DropInPaths,ExecStart,WorkingDirectory,EnvironmentFiles,User,Group,Triggers,TriggeredBy'])
  units[name]=props
  for line in props.splitlines():
   if line.startswith(('FragmentPath=','DropInPaths=')):
    for value in line.split('=',1)[1].split():
     if value.startswith('/etc/systemd/') or value.startswith('/usr/lib/systemd/'):copyfile(Path(value))
 (root/'unidades.json').write_text(json.dumps(units,ensure_ascii=False,indent=2)+'\n')
 # A single transaction spans both independent postal databases. No locks/flush.
 available=set(run(['mariadb','--no-defaults','--protocol=socket','--user=root','--batch','--skip-column-names','-e','SHOW DATABASES']).splitlines())
 databases=[n for n in ('santafe_comunidade','paodocafe') if n in available]
 if set(databases)!={'santafe_comunidade','paodocafe'}:raise RuntimeError('réplica completa exige ambos os bancos')
 engines=run(['mariadb','--no-defaults','--protocol=socket','--user=root','--batch','--skip-column-names','-e',"SELECT DISTINCT ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA IN ('santafe_comunidade','paodocafe') AND TABLE_TYPE='BASE TABLE'"]).splitlines()
 if not engines or any(x!='InnoDB' for x in engines):raise RuntimeError('tabela não transacional; snapshot exige estratégia específica')
 sql=root/'bancos.sql'
 with sql.open('xb') as f:
  proc=subprocess.run(['mariadb-dump','--no-defaults','--protocol=socket','--user=root','--single-transaction','--quick','--skip-lock-tables','--hex-blob','--routines','--triggers','--databases',*databases],stdout=f,stderr=subprocess.PIPE,timeout=900,preexec_fn=lambda:resource.setrlimit(resource.RLIMIT_FSIZE,(2*1024**3,2*1024**3)))
 if proc.returncode:
  (root/'sql-erros.txt').write_bytes(proc.stderr)
  raise RuntimeError('exportação SQL falhou; diagnóstico privado preservado')
 for name in roots:
  src=Path(name)
  if not src.exists():continue
  if src.is_file():copyfile(src)
  else:
   for folder,dirs,fnames in os.walk(src,followlinks=False):
    dirs[:]=[d for d in dirs if d not in ('node_modules','.git','cache','logs') and not (Path(folder)/d).is_symlink()]
    for n in fnames:
     f=Path(folder)/n
     try:copyfile(f)
     except FileNotFoundError:changes.append(str(f))
 if changes:raise RuntimeError('arquivos mudaram durante a cópia; não considerar snapshot consistente')
 # Recheck configuration and code after data copy, without exposing contents.
 for n,m in files.items():
  if not n.startswith(('var/lib/',)):
   if sha256(Path('/'+n))!=m['sha256']:raise RuntimeError('configuração/fonte mudou durante a cópia')
 manifest={'formato':1,'data':time.strftime('%Y-%m-%dT%H:%M:%S%z'),'bancos':databases,'arquivos':files,'sql_sha256':sha256(sql),'limite':'SQL transacional; depósitos lidos depois. Exigir verificação de todos os objetos referenciados antes de homologar. Não é snapshot atômico de disco/SQL.'}
 (root/'manifesto.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 (root/'PRONTO_PARA_ADAPTAR').write_text('Não executar sem isolamento e substituição dos destinos/credenciais externos.\n')
 print('REPLICA_CAPTURADA',root,len(files),'arquivos;',len(databases),'bancos; serviços inalterados')
except Exception as e:
 (root/'FALHA.txt').write_text(str(e)+'\n')
 print('REPLICA_INCOMPLETA',root,'— diagnóstico privado em FALHA.txt')
 raise SystemExit(1)
finally:
 for folder,dirs,fnames in os.walk(root):
  os.chown(folder,owner.pw_uid,owner.pw_gid);os.chmod(folder,0o700)
  for n in fnames:os.chown(Path(folder)/n,owner.pw_uid,owner.pw_gid);os.chmod(Path(folder)/n,0o600)
