#!/usr/bin/env python3
"""Reutiliza SOMENTE a réplica de ensaio encerrada; rede externa inexistente."""
from pathlib import Path
import argparse,concurrent.futures,hashlib,importlib.util,json,os,re,shutil,subprocess,sys,threading,time,traceback
R=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('replica12',Path(__file__).with_name('migrar-replica.py'));M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)

class Carga(M.Replica):
 def start(self,name,args,env=None,cwd=None):return super().start('dados14-'+name,args,env,cwd)
 def reuse(self):
  M.ensure(self.lab.name.startswith('santafe-migracao11-') and self.lab.parent==Path('/var/tmp'),'laboratório não autorizado')
  original=self.lab/'registros-dados11/resultado.json'
  previous=json.loads((original if original.is_file() else self.lab/'resultado.json').read_text())
  M.ensure(previous['resultado']=='PASSOU' and len(previous['grupos'])==23,'exige réplica encerrada e aprovada')
  M.ensure(shutil.disk_usage(self.lab).free>=2300*1024**2,'reserva inicial insuficiente')
  saved=self.lab/'registros-dados11'
  if not saved.exists():
   saved.mkdir()
   for p in self.lab.iterdir():
    if p.is_file() and p.suffix in ('.json','.log','.txt','.bin'):shutil.copy2(p,saved/p.name)
  else:M.ensure(json.loads((saved/'resultado.json').read_text())==previous,'registro original divergente')
  g=self.lab/'candidata'
  for part in ('bin','sls','pacotes','c','fe','pc'):
   self.run(['bash',self.stage/'ferramentas/instalar-arquivos.sh',part,g/'local','linux','0.0.0-dados.14'],cwd=self.stage)
  for name in ('arquivo','rede','mariadb','segredo','tomada'):
   shutil.copy2(self.stage/f'bibs/bibc/{name}/{name}.so',g/f'local/lib/santafé/1.0/bibc/{name}.so')
  for kind in ('estavel','candidata'):self.mount(self.lab/kind)
  (self.lab/'temporarios-db12').mkdir(mode=0o700,exist_ok=True)
  self.dbport=13306
  p=self.start('banco',[shutil.which('mariadbd') or '/usr/sbin/mariadbd','--no-defaults','--user=root','--tmpdir='+str(self.lab/'temporarios-db12'),'--datadir='+str(self.lab/'dados'),'--socket='+str(self.lab/'b.sock'),'--pid-file='+str(self.lab/'pid'),'--bind-address=127.0.0.1','--port=13306','--skip-log-bin','--event-scheduler=DISABLED','--local-infile=0','--skip-symbolic-links','--secure-file-priv='+str(self.lab/'exportacao'),'--plugin-dir='+str(self.lab/'sem-plugins'),'--innodb-buffer-pool-size=64M','--max-connections=60'])
  self.wait(p,13306)
  M.ensure(Path(self.sql('SELECT @@tmpdir;').strip()).resolve()==(self.lab/'temporarios-db12').resolve(),'temporários não isolados')
  self.password='ensaio-apenas-replica-11';self.user='réplica11';self.tokens={};self.owners={}
  for i,db in enumerate(M.DBS):
   self.owners[db]=int(self.sql('SELECT id FROM usuarios WHERE usuario='+M.quote(self.user)+';',db))
   for owner in map(int,self.sql('SELECT DISTINCT usuario_id FROM correio_caixas ORDER BY usuario_id;',db).splitlines()):
    self.tokens[(db,owner)]='replica11-'+str(i)+'-'+str(owner)
   # Somente sessões sintéticas já criadas pelo ensaio anterior.
   self.sql("UPDATE sessoes SET expira_em=DATE_ADD(NOW(),INTERVAL 1 DAY) WHERE csrf_token='replica11-csrf';",db)
  self.passed('réplica reutilizada sem duplicação de bancos e depósitos',**self.objects())
  self.installed()
 def load(self):
  duration=self.a.segundos;stop=threading.Event();samples=[];failures=[];counts=[0]*6;lat=[[] for _ in range(6)]
  free0=shutil.disk_usage(self.lab).free;start=time.monotonic();deadline=start+duration
  def sample():
   free=shutil.disk_usage(self.lab).free;rss=0;fds=0
   # O /proc pertence ao namespace privado: inclui também os trabalhadores
   # nginx e o executor, sem contar processos do servidor operacional.
   for proc in (self.lab/'candidata/proc').glob('[0-9]*'):
    try:
     text=(proc/'status').read_text();match=re.search(r'VmRSS:\s*(\d+)',text)
     if match:rss+=int(match.group(1))
     fds+=len(list((proc/'fd').iterdir()))
    except (FileNotFoundError,ProcessLookupError):pass
   M.ensure(rss>0 and fds>0,'monitor sem visibilidade dos processos isolados')
   M.ensure(not (self.lab/'INTERROMPER-DADOS14').exists(),'interrupção solicitada ao laboratório')
   available=int(re.search(r'MemAvailable:\s*(\d+)',Path('/proc/meminfo').read_text()).group(1))
   # Contar também .pulso.<carimbo> e outros arquivos rotacionados.
   for retry in range(3):
    try:
     logs=sum(p.stat().st_size for p in self.lab.iterdir() if p.is_file() and p.suffix in ('.log','.pulso','.jsonl'))
     logs+=sum(p.stat().st_size for p in (self.lab/'candidata/var/log').rglob('*') if p.is_file())
     logs+=sum(p.stat().st_size for p in self.i.rglob('*') if p.is_file() and p.suffix=='.log')
     break
    except FileNotFoundError:
     if retry==2:raise
   row={'s':round(time.monotonic()-start,1),'livre_mib':free//2**20,'rss_kib':rss,'memoria_disponivel_kib':available,'descritores':fds,'registros_bytes':logs,'operacoes':sum(counts)};samples.append(row)
   M.ensure(free>=2*1024**3,'disco abaixo da reserva 2 GiB')
   M.ensure(free0-free<=256*1024**2,'crescimento de disco acima de 256 MiB')
   M.ensure(rss<=1536*1024 and available>=768*1024,'memória excedeu orçamento')
   M.ensure(logs<=128*1024**2 and fds<=2048,'registros/descritores excederam orçamento')
   M.ensure(all(p.poll() is None for p in services),'serviço encerrou durante carga')
   return row
  def monitor():
   try:
    while not stop.is_set():
     row=sample();M.write(self.lab/'progresso-dados14.json',row);stop.wait(5)
   except BaseException as e:failures.append(str(e));stop.set()
  def worker(i):
   tokens=[t for(d,u),t in self.tokens.items() if d==M.DBS[i%2]]
   try:
    while time.monotonic()<deadline and not stop.is_set():
     t=time.monotonic();status,body=self.http(17100+i%2,'/carteiro/entrada',tokens[counts[i]%len(tokens)])
     M.ensure(status==200,'HTTP '+str(status)+' no leitor '+str(i))
     counts[i]+=1;lat[i].append(time.monotonic()-t)
     stop.wait(max(0,.5-(time.monotonic()-t))) # máximo 12 pedidos/s agregados
   except BaseException as e:failures.append(str(e));stop.set()
  services=[p for p in self.procs if p.poll() is None]
  watcher=threading.Thread(target=monitor);watcher.start()
  try:
   with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:list(pool.map(worker,range(6)))
   sample();M.ensure(not failures,'carga interrompida: '+str(failures));M.ensure(time.monotonic()-start>=duration,'carga incompleta')
   values=sorted(v for arr in lat for v in arr)
   self.passed('carga prolongada da réplica',segundos=round(time.monotonic()-start,2),operacoes=sum(counts),clientes=6,p95_ms=round(values[int(len(values)*.95)]*1000,2),rss_max_kib=max(x['rss_kib'] for x in samples),disco_livre_min_mib=min(x['livre_mib'] for x in samples))
  finally:
   stop.set();watcher.join();M.write(self.lab/'carga-dados14.json',{'resultado':'FALHOU' if failures or time.monotonic()-start<duration else 'PASSOU','segundos':round(time.monotonic()-start,2),'contadores':counts,'amostras':samples,'falhas':failures,'limite_pedidos_por_segundo':12})
 def execute(self):
  self.reuse();before=self.tables();procs=self.services('candidata');procs+=self.infrastructure('candidata')
  M.ensure(self.tables()==before,'inicialização modificou dados')
  self.read_all('candidata');self.load()
  for i in range(2):self.message('dados14-depois',i)
  self.protocols('candidata','dados14-depois');self.read_all('candidata');self.objects();self.stop(procs)
  before=self.tables();procs=self.services('estavel');procs+=self.infrastructure('estavel');M.ensure(self.tables()==before,'reversão modificou dados')
  self.read_all('estavel');self.objects();self.stop(procs)
  self.passed('reversão preservou novas escritas após carga prolongada')
  self.report['resultado']='PASSOU'

def main():
 p=argparse.ArgumentParser();p.add_argument('--lab',type=Path,required=True);p.add_argument('--replica',type=Path,required=True);p.add_argument('--candidato',type=Path,required=True);p.add_argument('--segundos',type=int,default=3600);p.add_argument('--interior',action='store_true');a=p.parse_args()
 M.ensure(3600<=a.segundos<=7200,'exige uma a duas horas');M.ensure((a.candidato/'.laboratorio-dados14').is_file(),'candidato incorreto')
 if not a.interior:
  env=dict(M.BASE_ENV,SANTAFE_NET_ORIGEM=os.readlink('/proc/self/ns/net'));os.nice(15)
  raise SystemExit(subprocess.call(['unshare','--user','--map-root-user','--mount','--net','--pid','--fork',sys.executable,str(Path(__file__).resolve()),*sys.argv[1:],'--interior'],env=env))
 M.ensure(os.getpid()==1 and os.readlink('/proc/self/ns/net')!=os.environ['SANTAFE_NET_ORIGEM'],'namespace obrigatório')
 M.ensure({x['ifname'] for x in json.loads(subprocess.check_output(['ip','-j','link']))}=={'lo'},'rede externa presente');subprocess.run(['ip','link','set','lo','up'],check=True)
 os.umask(0o077);x=Carga(a)
 try:x.execute()
 except BaseException as e:
  x.report['resultado']='FALHOU';x.report['falha']=str(e) if type(e) is RuntimeError else type(e).__name__
  (x.lab/'rastro-dados14-privado.txt').write_text(traceback.format_exc());print('FALHOU',x.report['falha'],flush=True)
 finally:
  x.stop(x.procs)
  for h in x.handles:h.close()
  M.write(x.lab/'resultado-dados14.json',x.report)
 if x.report['resultado']!='PASSOU':raise SystemExit(1)
if __name__=='__main__':main()
