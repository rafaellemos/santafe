#!/usr/bin/env python3
"""Emissão/renovação ACME real em Pebble, com Certbot privado e sem rede externa."""
from pathlib import Path
import argparse,hashlib,json,os,shutil,socket,ssl,subprocess,sys,tempfile,time,urllib.request
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('--dependencias',type=Path,required=True);p.add_argument('--interior',action='store_true');a=p.parse_args()
assert(ROOT/'.laboratorio-dados13').is_file()
assert a.dependencias.name.startswith('santafe-acme13-') and a.dependencias.parent==Path('/tmp')
if not a.interior:
 env={k:os.environ[k] for k in ['PATH','LANG','LC_ALL'] if k in os.environ};env['ENSAIO_NET_ORIGEM']=os.readlink('/proc/self/ns/net')
 raise SystemExit(subprocess.call(['unshare','--user','--map-root-user','--mount','--net','--pid','--fork','--mount-proc',sys.executable,str(Path(__file__).resolve()),*sys.argv[1:],'--interior'],env=env))
assert os.getpid()==1 and os.readlink('/proc/self/ns/net')!=os.environ['ENSAIO_NET_ORIGEM']
assert {x['ifname'] for x in json.loads(subprocess.check_output(['ip','-j','link']))}=={'lo'}
subprocess.run(['ip','link','set','lo','up'],check=True);os.umask(0o077)
lab=Path(tempfile.mkdtemp(prefix='santafe-cert13-',dir='/tmp'));procs=[];handles=[]
env={k:os.environ[k] for k in ['PATH','LANG','LC_ALL'] if k in os.environ};env.update(HOME=str(lab),PEBBLE_VA_NOSLEEP='1',PEBBLE_WFE_NONCEREJECT='0',PEBBLE_AUTHZREUSE='0')
r={'resultado':'EM_ANDAMENTO','grupos':[],'laboratorio':str(lab),'acme':'Pebble 2.10.1','certificados_publicos_alterados':False,'rede_externa':False}
def run(name,cmd,ok=True):
 with (lab/(name+'.log')).open('wb') as log:res=subprocess.run(list(map(str,cmd)),env=env,cwd=ROOT,stdout=log,stderr=log,timeout=150)
 if ok:assert res.returncode==0,name+' falhou'
 return res.returncode
def start(name,cmd):
 log=(lab/(name+'.log')).open('wb');handles.append(log)
 p=subprocess.Popen(list(map(str,cmd)),env=env,cwd=ROOT,stdout=log,stderr=log);procs.append(p);return p
def wait(p,port):
 for _ in range(150):
  assert p.poll() is None,'processo encerrou'
  try:
   with socket.create_connection(('127.0.0.1',port),timeout=.2):return
  except OSError:time.sleep(.1)
 raise AssertionError('porta não iniciou')
def stop(p):
 if p.poll() is None:
  p.terminate()
  try:p.wait(timeout=10)
  except subprocess.TimeoutExpired:p.kill();p.wait()
def passed(s):r['grupos'].append(s);print('PASSOU',s,flush=True)
try:
 run('certificado-acme',['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',lab/'acme-key.pem','-out',lab/'acme-cert.pem','-days','2','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost,IP:127.0.0.1'])
 env['REQUESTS_CA_BUNDLE']=str(lab/'acme-cert.pem')
 dns=start('dns',[a.dependencias/'pebble-challtestsrv','-dnsserver','127.0.0.1:18053','-management','127.0.0.1:18055','-http01','','-https01','','-tlsalpn01','','-doh','','-defaultIPv6',''])
 wait(dns,18055)
 config={'pebble':{'listenAddress':'127.0.0.1:14000','managementListenAddress':'127.0.0.1:15000','certificate':str(lab/'acme-cert.pem'),'privateKey':str(lab/'acme-key.pem'),'httpPort':15002,'tlsPort':15001,'ocspResponderURL':'','externalAccountBindingRequired':False}}
 (lab/'pebble.json').write_text(json.dumps(config))
 ca=start('pebble',[a.dependencias/'pebble','-config',lab/'pebble.json','-dnsserver','127.0.0.1:18053']);wait(ca,14000)
 common=['certbot','--config-dir',lab/'config','--work-dir',lab/'work','--logs-dir',lab/'logs','--server','https://localhost:14000/dir','--non-interactive','--no-random-sleep-on-renew','--no-directory-hooks','--no-eff-email']
 domain='cert.ensaio.test'
 run('emitir',common+['certonly','--standalone','--http-01-address','127.0.0.1','--http-01-port','15002','--preferred-challenges','http','--agree-tos','--register-unsafely-without-email','--cert-name',domain,'-d',domain])
 live=lab/'config/live'/domain
 ctx=ssl.create_default_context(cafile=str(lab/'acme-cert.pem'))
 with urllib.request.urlopen('https://localhost:15000/roots/0',context=ctx,timeout=10) as f:(lab/'raiz-emitida.pem').write_bytes(f.read())
 trust=ssl.create_default_context(cafile=str(lab/'raiz-emitida.pem'))
 bootstrap='módulo.caminho="bibs/bibf/?.fé;bibs/bibf/?/?.fé";módulo.caminhoC="bibs/bibc/?/?.so";'
 code='local c=importe "correio";local r=importe "rede";local s=garanta(c.servidor{endereço="127.0.0.1",porta=15993,nome="'+domain+'",segurança="TLS",certificado='+json.dumps(str(live/'fullchain.pem'))+',chavePrivada='+json.dumps(str(live/'privkey.pem'))+',domíniosLocais={"ensaio.test"},receba=função(_,fimDaCarta) fimDaCarta(verdadeiro) fim});garanta(s:inicie());r.laço()'
 def observe():
  with socket.create_connection(('127.0.0.1',15993),timeout=10) as raw,trust.wrap_socket(raw,server_hostname=domain) as c:
   assert c.recv(1024).startswith(b'220 ')
   return hashlib.sha256(c.getpeercert(True)).hexdigest()
 srv=start('smtp-primeiro',[ROOT/'src/santafé','-E','-P','-e',bootstrap+code]);wait(srv,15993);first=observe();stop(srv)
 passed('Certbot/Pebble: HTTP-01 e certificado carregado pelo servidor TLS candidato')
 run('renovar',common+['renew','--cert-name',domain,'--force-renewal'])
 srv=start('smtp-renovado',[ROOT/'src/santafé','-E','-P','-e',bootstrap+code]);wait(srv,15993);second=observe()
 assert first!=second
 passed('Renovação ACME: certificado novo servido e cadeia/nome verificados')
 # CA indisponível: não pode destruir o certificado vigente ou o par de chaves.
 before={n:hashlib.sha256((live/n).read_bytes()).hexdigest() for n in ['cert.pem','chain.pem','fullchain.pem','privkey.pem']}
 stop(ca)
 assert run('renovacao-sem-ca',common+['renew','--cert-name',domain,'--force-renewal'],ok=False)!=0
 after={n:hashlib.sha256((live/n).read_bytes()).hexdigest() for n in before}
 assert before==after and observe()==second
 passed('CA indisponível: renovação falha e certificado vigente continua utilizável')
 r.update(resultado='PASSOU',certificado_inicial_sha256=first,certificado_renovado_sha256=second)
finally:
 for p in reversed(procs):stop(p)
 for h in handles:h.close()
 r['disco_livre_mib']=shutil.disk_usage(lab).free//1024**2
 (ROOT/'evidencias').mkdir(exist_ok=True)
 (ROOT/'evidencias/acme13.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
