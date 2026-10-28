#!/usr/bin/env python3
"""Certbot/Pebble reais usando o auxiliar novo, só loopback no namespace."""
from pathlib import Path
import argparse,hashlib,http.server,importlib.util,json,os,shutil,socket,socketserver,ssl,subprocess,sys,tempfile,threading,time,urllib.request
p=argparse.ArgumentParser();p.add_argument('--dependencias',type=Path,required=True);p.add_argument('--interior',action='store_true');a=p.parse_args()
if not a.interior:
 env={k:os.environ[k] for k in ['PATH','LANG','LC_ALL'] if k in os.environ};env['NET_ORIGEM']=os.readlink('/proc/self/ns/net')
 raise SystemExit(subprocess.call(['unshare','--user','--map-root-user','--mount','--net','--pid','--fork','--mount-proc',sys.executable,str(Path(__file__).resolve()),*sys.argv[1:],'--interior'],env=env))
assert os.getpid()==1 and os.readlink('/proc/self/ns/net')!=os.environ['NET_ORIGEM']
assert {x['ifname'] for x in json.loads(subprocess.check_output(['ip','-j','link']))}=={'lo'}
subprocess.run(['ip','link','set','lo','up'],check=True);os.umask(0o077)
spec=importlib.util.spec_from_file_location('A',Path(__file__).with_name('acme-publico.py'));A=importlib.util.module_from_spec(spec);spec.loader.exec_module(A)
lab=Path(tempfile.mkdtemp(prefix='santafe-acme-publico15-',dir='/var/tmp'));procs=[];handles=[];groups=[]
for n in ['tokens','web']:(lab/n).mkdir()
(lab/'web/.well-known/acme-challenge').mkdir(parents=True)
(lab/'vazio.ini').write_text('');shutil.copy2(Path(__file__).with_name('acme-publico.py'),lab/'roteiro.py')
A.save(lab/'contexto.json',{'dominio':A.DOMAIN,'desafios':str(lab/'web/.well-known/acme-challenge'),'origem_http':'http://127.0.0.1:15002'})
def start(name,args):
 h=(lab/(name+'.log')).open('wb');handles.append(h);q=subprocess.Popen(list(map(str,args)),env=A.ENV,stdout=h,stderr=h);procs.append(q);return q
def wait(q,port):
 for _ in range(150):
  assert q.poll() is None
  try:
   with socket.create_connection(('127.0.0.1',port),timeout=.2):return
  except OSError:time.sleep(.1)
 raise AssertionError('porta indisponível')
def passed(s):groups.append(s);print('PASSOU',s,flush=True)
class Handler(http.server.SimpleHTTPRequestHandler):
 def __init__(self,*args,**kw):super().__init__(*args,directory=str(lab/'web'),**kw)
 def log_message(self,*args):pass
server=socketserver.ThreadingTCPServer(('127.0.0.1',15002),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
try:
 A.run(lab,'ca-tls',['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(lab/'acme-key.pem'),'-out',str(lab/'acme-cert.pem'),'-days','2','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost,IP:127.0.0.1'])
 A.ENV.update(REQUESTS_CA_BUNDLE=str(lab/'acme-cert.pem'),PEBBLE_VA_NOSLEEP='1',PEBBLE_WFE_NONCEREJECT='0',PEBBLE_AUTHZREUSE='0')
 dns=start('dns',[a.dependencias/'pebble-challtestsrv','-dnsserver','127.0.0.1:18053','-management','127.0.0.1:18055','-http01','','-https01','','-tlsalpn01','','-doh','','-defaultIPv6','']);wait(dns,18055)
 A.save(lab/'pebble.json',{'pebble':{'listenAddress':'127.0.0.1:14000','managementListenAddress':'127.0.0.1:15000','certificate':str(lab/'acme-cert.pem'),'privateKey':str(lab/'acme-key.pem'),'httpPort':15002,'tlsPort':15001,'ocspResponderURL':'','externalAccountBindingRequired':False}})
 ca=start('ca',[a.dependencias/'pebble','-config',lab/'pebble.json','-dnsserver','127.0.0.1:18053']);wait(ca,14000)
 A.SERVER='https://localhost:14000/dir'
 common=['certbot','-c',str(lab/'vazio.ini'),'--config-dir',str(lab/'config'),'--work-dir',str(lab/'work'),'--logs-dir',str(lab/'logs'),'--server',A.SERVER,'--non-interactive']
 A.run(lab,'conta-local',common+['register','--agree-tos','--register-unsafely-without-email'])
 regs=list((lab/'config/accounts').rglob('regr.json'));assert len(regs)==1;account=regs[0].parent.name
 A.run(lab,'emissao',A.command(lab,account))
 ctx=ssl.create_default_context(cafile=str(lab/'acme-cert.pem'))
 with urllib.request.urlopen('https://localhost:15000/roots/0',context=ctx,timeout=10) as f:(lab/'raiz.pem').write_bytes(f.read())
 A.TRUST=str(lab/'raiz.pem');first=A.inspect_cert(lab)
 assert list((lab/'tokens').glob('*.json')) and all(A.read(f)['http_conferido'] and A.read(f)['limpo'] for f in (lab/'tokens').glob('*.json'))
 assert not list((lab/'web/.well-known/acme-challenge').iterdir())
 passed('Certbot real: autorização HTTP do auxiliar, cadeia, SAN, chave e limpeza')
 A.run(lab,'renovacao',A.command(lab,account,True));second=A.inspect_cert(lab);assert second!=first
 assert len(list((lab/'tokens').glob('*.json')))==2 and not list((lab/'web/.well-known/acme-challenge').iterdir())
 passed('renovação real repete desafio e preserva isolamento dos diretórios')
 before=A.hashes(lab/'config/live');ca.terminate();ca.wait(timeout=10)
 try:A.run(lab,'ca-indisponivel',A.command(lab,account,True),timeout=30)
 except (RuntimeError,subprocess.TimeoutExpired):pass
 else:raise AssertionError('CA indisponível aceita')
 assert A.hashes(lab/'config/live')==before and A.inspect_cert(lab)==second
 passed('CA indisponível não apaga certificado vigente')
finally:
 for q in reversed(procs):
  if q.poll() is None:q.terminate();q.wait(timeout=10)
 for h in handles:h.close()
 server.shutdown();server.server_close();thread.join(timeout=2)
 report={'resultado':'PASSOU' if len(groups)==3 else 'FALHOU','grupos':groups,'rede_externa':False,'ca':'Pebble local; não comprova emissão pública'}
 A.save(lab/'resultado-integrado.json',report);print('EVIDENCIA',lab/'resultado-integrado.json')
assert len(groups)==3
