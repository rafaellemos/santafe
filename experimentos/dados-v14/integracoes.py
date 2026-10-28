"""Infraestrutura real de homologação; exige namespace sem saída e cópias privadas."""
from pathlib import Path
import base64,hashlib,http.client,json,os,shutil,signal,socket,ssl,smtplib,subprocess,tempfile,time,urllib.request
DOMS=['xn--santaf-gva.dev.br','xn--podocaf-xwa4d.com.br']
class Integracoes:
 def private_run(self,name,args,env=None,ok=True):
  with (self.i/(name+'.log')).open('wb') as f:
   r=subprocess.run(list(map(str,args)),env=env or self.baseenv,stdout=f,stderr=f,timeout=180)
  if ok:assert r.returncode==0,name+' falhou (registro privado)'
  return r.returncode
 def setup_integrations(self):
  self.i=Path(tempfile.mkdtemp(prefix='santafe-integracoes14-',dir='/tmp'));self.g=self.lab/'candidata'
  self.baseenv={k:os.environ[k] for k in ('PATH','LANG','LC_ALL') if k in os.environ}
  self.baseenv.update(HOME=str(self.i),GSETTINGS_BACKEND='memory')
  for root in ('estavel','candidata'):
   hosts=self.lab/root/'etc/hosts';text=hosts.read_text()
   if 'retransmissor.ensaio.test' not in text:hosts.write_text(text+'\n127.0.0.1 retransmissor.ensaio.test\n')
  self.private_run('chave-dkim',['openssl','genpkey','-algorithm','RSA','-pkeyopt','rsa_keygen_bits:2048','-out',self.i/'dkim.pem'])
  self.private_run('publica-dkim',['openssl','pkey','-in',self.i/'dkim.pem','-pubout','-outform','DER','-out',self.i/'dkim.der'])
  shutil.copyfile(self.i/'dkim.pem',self.g/'tmp/dkim14.pem')
  key='v=DKIM1; k=rsa; p='+base64.b64encode((self.i/'dkim.der').read_bytes()).decode()
  zones=[]
  for domain in DOMS+['ensaio.invalid','retransmissor.ensaio.test','recusado.test','invalid','test','br','dev.br','com.br']:
   spf='v=spf1 -all' if domain=='recusado.test' else 'v=spf1 ip4:127.0.0.1 -all'
   records=['{nome="@",tipo="SOA",dados={mestre="ns",responsável="dns",série=1,atualização=60,novaTentativa=30,expiração=600,mínimo=1}}',
    '{nome="@",tipo="NS",dados="ns"}','{nome="ns",tipo="A",dados="127.0.0.1"}',
    '{nome="@",tipo="A",dados="127.0.0.1"}',
    '{nome="@",tipo="TXT",dados='+json.dumps(spf)+'}',
    '{nome="_dmarc",tipo="TXT",dados="v=DMARC1; p=reject; adkim=s; aspf=s"}',
    '{nome="ensaio14._domainkey",tipo="TXT",dados={'+','.join(json.dumps(key[i:i+240]) for i in range(0,len(key),240))+'}}']
   if domain in ('invalid','test','br','dev.br','com.br'):records=records[:3]
   zones.append('{nome='+json.dumps(domain)+',registros={'+','.join(records)+'}}')
  script='local a=importe "nomes.autoridade";local r=importe "rede";local s=garanta(a.novo{endereço="127.0.0.1",porta=53,zonas={'+','.join(zones)+'}});garanta(s:inicie());r.laço()'
  dns=self.start('dns-autenticacao',self.command(self.g,code=script),self.env_unit(self.g,'carteiro.service'));self.wait(dns,53)
  for domain in DOMS+['ensaio.invalid','recusado.test']:
   for name in (domain,'_dmarc.'+domain):
    answer=self.run(['dig','@127.0.0.1',name,'TXT','+noall','+comments','+answer','+time=2','+tries=1']).decode()
    assert 'status: NOERROR' in answer and '"v=' in answer,'DNS TXT sintético não respondeu: '+name
  code='local r=importe "rede";r.consulteDNSAssíncrono("ensaio.invalid","TXT",função(a,f) mostre(json.cod({resposta=a,falha=f}));r.pareLaço() fim);r.laço()'
  (self.i/'dns-sintetico.json').write_text(self.sf('candidata',code))
  self.acme_prepare()
  self.clam_start()
  shutil.copy2(self.stage/'experimentos/dados-v14/retransmissor.fé',self.g/'tmp/retransmissor14.fé')
  self.relay=self.start('retransmissor',self.command(self.g,code='executeArquivo("/tmp/retransmissor14.fé")'),self.env_unit(self.g,'carteiro.service'));self.wait(self.relay,12587)
  self.relay_probe()
  self.passed('proteções conjuntas: DNS de ensaio, ClamAV real, retransmissor TLS AUTH e ACME local ativos')
 def relay_probe(self):
  with smtplib.SMTP('127.0.0.1',12587,timeout=10) as c:
   c.ehlo();c.starttls(context=self.client_tls());c.ehlo();c.login('ensaio14','somente-ensaio14')
   assert c.mail('origem@ensaio.invalid',options=['SMTPUTF8','BODY=8BITMIME'])[0]==250
   for domain in DOMS:assert c.rcpt('réplica11@'+domain)[0]==250
   assert c.rcpt('destino@externo.invalid')[0]==550,'retransmissor permitiu destinatário externo'
   c.rset()
 def acme_prepare(self):
  self.private_run('acme-tls',['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',self.i/'acme-key.pem','-out',self.i/'acme-cert.pem','-days','2','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost,IP:127.0.0.1'])
  self.caenv=dict(self.baseenv,REQUESTS_CA_BUNDLE=str(self.i/'acme-cert.pem'),PEBBLE_VA_NOSLEEP='1',PEBBLE_WFE_NONCEREJECT='0',PEBBLE_AUTHZREUSE='0')
  deps=self.a.acme
  origins=json.loads((deps/'origens.json').read_text())
  for name in ('pebble','pebble-challtestsrv'):
   entry=next(x for x in origins if ('/'+name+'-linux-amd64.tar.gz') in x['url'])
   assert hashlib.sha256((deps/name).read_bytes()).hexdigest()==entry['executavel_sha256']
  dns=self.start('acme-dns',[deps/'pebble-challtestsrv','-dnsserver','127.0.0.1:18053','-management','127.0.0.1:18055','-http01','','-https01','','-tlsalpn01','','-doh','','-defaultIPv6',''],self.caenv);self.wait(dns,18055)
  cfg={'pebble':{'listenAddress':'127.0.0.1:14000','managementListenAddress':'127.0.0.1:15000','certificate':str(self.i/'acme-cert.pem'),'privateKey':str(self.i/'acme-key.pem'),'httpPort':15002,'tlsPort':15001,'ocspResponderURL':'','externalAccountBindingRequired':False}}
  (self.i/'pebble.json').write_text(json.dumps(cfg))
  self.ca=self.start('acme',[deps/'pebble','-config',self.i/'pebble.json','-dnsserver','127.0.0.1:18053'],self.caenv);self.wait(self.ca,14000)
  self.certcmd=['certbot','--config-dir',self.i/'config','--work-dir',self.i/'work','--logs-dir',self.i/'logs','--server','https://localhost:14000/dir','--non-interactive','--no-random-sleep-on-renew','--no-directory-hooks','--no-eff-email']
  self.private_run('emitir',self.certcmd+['certonly','--standalone','--http-01-address','127.0.0.1','--http-01-port','15002','--preferred-challenges','http','--agree-tos','--register-unsafely-without-email','--cert-name','conjunto14']+sum((['-d',x] for x in DOMS+['retransmissor.ensaio.test']),[]),self.caenv)
  ctx=ssl.create_default_context(cafile=str(self.i/'acme-cert.pem'))
  with urllib.request.urlopen('https://localhost:15000/roots/0',context=ctx,timeout=10) as f:(self.i/'raiz.pem').write_bytes(f.read())
  trust=self.g/'etc/ssl/certs/ca-certificates.crt';trust.parent.mkdir(parents=True,exist_ok=True)
  assert str(trust.resolve()).startswith(str(self.g)+'/'),'confiança fora da cópia'
  trust.write_bytes((self.i/'raiz.pem').read_bytes())
  self.install_certificate()
 def install_certificate(self):
  live=self.i/'config/live/conjunto14'
  for src,dst in [('fullchain.pem','tls-certificado.pem'),('privkey.pem','tls-chave.pem')]:
   temp=self.g/'tmp'/('novo-'+dst);temp.write_bytes((live/src).read_bytes());temp.chmod(0o600);os.replace(temp,self.g/'tmp'/dst)
 def client_tls(self):
  ctx=ssl.create_default_context(cafile=str(self.i/'raiz.pem'));wrap=ctx.wrap_socket
  def wrapped(*args,**kw):
   if kw.get('server_hostname')=='127.0.0.1':kw['server_hostname']=DOMS[0]
   return wrap(*args,**kw)
  ctx.wrap_socket=wrapped
  return ctx
 def certificate(self,port=443):
  with socket.create_connection(('127.0.0.1',port),timeout=10) as raw,self.client_tls().wrap_socket(raw,server_hostname=DOMS[0]) as s:
   return hashlib.sha256(s.getpeercert(True)).hexdigest()
 def renew(self):
  before=self.certificate()
  self.private_run('renovar',self.certcmd+['renew','--cert-name','conjunto14','--force-renewal'],self.caenv)
  self.install_certificate();self.nginx.send_signal(signal.SIGHUP)
  for _ in range(100):
   after=self.certificate()
   if after!=before:break
   time.sleep(.1)
  assert before!=after,'nginx não carregou certificado novo'
  self.passed('renovação ACME durante carga: nginx serve novo certificado sem encerrar leitores')
 def clam_start(self):
  signatures=self.stage/'evidencias/assinaturas14';signatures.mkdir(parents=True,exist_ok=True)
  if not(signatures/'daily.cld').exists():shutil.copyfile('/var/lib/clamav/daily.cld',signatures/'daily.cld')
  eicar=b'X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*'
  (signatures/'ensaio.hdb').write_text(hashlib.md5(eicar).hexdigest()+':'+str(len(eicar))+':Santafe.Ensaio.Eicar\n')
  cfg=self.i/'clamd.conf';cfg.write_text('Foreground yes\nTCPSocket 13310\nTCPAddr 127.0.0.1\nDatabaseDirectory '+str(signatures)+'\nTemporaryDirectory '+str(self.i)+'\nLogFile '+str(self.i/'clamd.log')+'\nLogFileMaxSize 2M\nMaxThreads 2\nMaxQueue 4\nStreamMaxLength 8M\nMaxScanSize 16M\nMaxFileSize 8M\nSelfCheck 0\n')
  self.clam=self.start('clamd',['/usr/sbin/clamd','--config-file='+str(cfg)],self.baseenv)
  for _ in range(600):
   assert self.clam.poll() is None,'clamd encerrou'
   try:
    with socket.create_connection(('127.0.0.1',13310),timeout=.3) as c:c.sendall(b'zPING\0');assert c.recv(32)==b'PONG\0'
    return
   except OSError:time.sleep(.1)
  raise RuntimeError('clamd não iniciou')
