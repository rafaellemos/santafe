#!/usr/bin/env python3
"""Ensaio privado da instalação capturada. Nunca instala nem reinicia produção.

Dados ficam no servidor. Apps rodam em chroot, rede/PID/montagens próprios;
somente OS em leitura e cópias privadas em escrita. O relatório público contém
contagens/hashes, nunca mensagens, contas, configurações ou erros SQL brutos.
"""
from pathlib import Path
import argparse, base64, concurrent.futures, email.policy, hashlib, http.client
import importlib.util, imaplib, json, os, re, shlex, shutil, smtplib, socket, ssl
import subprocess, sys, tempfile, time, traceback, urllib.parse
from email.message import EmailMessage

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('verifica',HERE.parent/'dados-v12/verificar-replica.py')
V=importlib.util.module_from_spec(spec);spec.loader.exec_module(V)
DBS=('santafe_comunidade','paodocafe')
DOMS=('xn--santaf-gva.dev.br','xn--podocaf-xwa4d.com.br')
DISPLAYDOMS=('santafé.dev.br','pãodocafé.com.br')
DEPS=('/var/lib/santafé/correio','/var/lib/paodocafe/correio')
BASE_ENV={k:os.environ[k] for k in ('PATH','LANG','LC_ALL') if k in os.environ}
BASE_ENV.update(GSETTINGS_BACKEND='memory',HOME='/tmp')

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ident(s):return '`'+s.replace('`','``')+'`'
def quote(s):return "'"+s.replace('\\','\\\\').replace("'","''")+"'"
def ensure(ok,label):
 if not ok:raise RuntimeError(label)
def write(p,value):p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')

class Replica:
 def __init__(self,a):
  self.a=a;self.lab=a.lab;self.root=a.replica/'arquivos';self.stage=a.candidato
  self.procs=[];self.handles=[];self.results=[];self.report={'resultado':'EM_ANDAMENTO','producao_alterada':False,'privado':True,'grupos':self.results}
 def passed(self,name,**counts):
  self.results.append({'grupo':name,**counts});print('PASSOU',name,json.dumps(counts),flush=True)
  write(self.lab/'resultado.json',self.report)
 def run(self,args,**kw):
  r=subprocess.run([str(x) for x in args],env=BASE_ENV,capture_output=True,timeout=120,**kw)
  if r.returncode:
   (self.lab/'falha-comando.log').write_bytes(r.stdout+r.stderr);raise RuntimeError('comando privado falhou: '+Path(args[0]).name)
  return r.stdout
 def start(self,name,args,env=None,cwd=None):
  h=(self.lab/(name+'.log')).open('wb');self.handles.append(h)
  p=subprocess.Popen([str(x) for x in args],env=env or BASE_ENV,cwd=cwd,stdout=h,stderr=h)
  self.procs.append(p);return p
 def stop(self,procs):
  for p in reversed(procs):
   if p.poll() is None:
    p.terminate()
    try:p.wait(timeout=15)
    except subprocess.TimeoutExpired:p.kill();p.wait()
 def wait(self,p,port):
  for _ in range(400):
   ensure(p.poll() is None,'processo encerrou antes da prontidão')
   try:
    with socket.create_connection(('127.0.0.1',port),timeout=.2):return
   except OSError:time.sleep(.05)
  raise RuntimeError('timeout de inicialização')
 def sql(self,q,db=None):
  args=['mariadb','--no-defaults','--protocol=socket','--socket='+str(self.lab/'b.sock'),'-uroot','--batch','--raw','--skip-column-names','--binary-mode','--local-infile=0']
  return self.run(args,input=(('USE '+ident(db)+';\n' if db else '')+q).encode()).decode()
 def tables(self):
  result={}
  for db in DBS:
   result[db]={}
   for tab in self.sql('SHOW FULL TABLES WHERE Table_type="BASE TABLE";',db).splitlines():
    tab=tab.split('\t')[0];q=ident(db)+'.'+ident(tab)
    result[db][tab]=[int(self.sql('SELECT COUNT(*) FROM '+q)),self.sql('CHECKSUM TABLE '+q+' EXTENDED;').strip().split('\t')[-1]]
  return result
 def objects(self):
  result={}
  for db,dep in zip(DBS,DEPS):
   refs=set()
   for t,c in (('correio_cartas','mime_objeto'),('correio_anexos','dados_objeto'),('correio_fila','conteudo_objeto')):
    refs.update(x for x in self.sql('SELECT DISTINCT '+ident(c)+' FROM '+ident(t)+' WHERE '+ident(c)+' IS NOT NULL;',db).splitlines() if x)
   for digest in refs:
    ensure(re.fullmatch('[0-9a-f]{64}',digest),'referência de objeto malformada')
    p=self.lab/'estado-lib'/dep.removeprefix('/var/lib/')/'objetos'/digest[:2]/digest[2:4]/digest
    ensure(p.is_file() and hashlib.blake2b(p.read_bytes(),digest_size=32).hexdigest()==digest,'objeto postal ausente/divergente')
   result[db]=len(refs)
  return result
 def prepare(self):
  m=V.conferir(self.a.replica)
  ensure((self.stage/'.laboratorio-dados10').is_file(),'candidato base inválido')
  # Estáticos nunca são escritos neste percurso. Montá-los em leitura evita
  # copiar todos os downloads do portal a cada geração/rodada.
  needed=sum(v['tamanho'] for n,v in m['arquivos'].items() if not n.startswith('var/www/'))*4+2*1024**3
  ensure(shutil.disk_usage(self.lab).free>needed,'espaço insuficiente: preservada reserva de 2 GiB')
  for kind in ('estavel','candidata'):
   g=self.lab/kind
   shutil.copytree(self.root,g,ignore=lambda folder,names: [n for n in names if Path(folder)==self.root/'var' and n in ('www','lib')])
   (g/'var/www').mkdir();(g/'var/lib').mkdir()
   # snapshot guardou binários sem bit de execução, deliberadamente.
   for n in ('santafé','santafec','santafé-sls'):
    if (g/'usr/local/bin'/n).exists():(g/'usr/local/bin'/n).chmod(0o700)
   shutil.move(g/'usr/local',g/'local');(g/'usr/local').mkdir()
   for n in ('tmp','run','proc','dev','sys','bin','sbin','lib','lib64'):(g/n).mkdir(exist_ok=True)
   for n in ('passwd','group','nsswitch.conf','hosts','ld.so.cache'):
    p=Path('/etc')/n
    if p.is_file():shutil.copy2(p,g/'etc'/n)
   (g/'etc/resolv.conf').write_text('nameserver 127.0.0.1\n')
   for n in ('null','zero','random','urandom'):(g/'dev'/n).touch()
   (g/'var/log/santafé').mkdir(parents=True,exist_ok=True);(g/'var/log/paodocafe').mkdir(parents=True,exist_ok=True)
   for n in ('certificado','chave'):
    shutil.copyfile(self.stage/f'testes/recursos/tls-local-{n}.pem',g/f'tmp/tls-{n}.pem')
  shutil.copytree(self.root/'var/lib',self.lab/'estado-lib')
  stable=self.lab/'estavel/local/bin/santafé';cand=self.lab/'candidata'
  migration=[]
  # Conversão léxica somente; não executa nenhum programa capturado.
  for tree in ('opt','etc','local/share'):
   for p in sorted((cand/tree).rglob('*.fé')):
    old=sha(p)
    r=subprocess.run([str(stable),'-E','-P',str(self.stage/'experimentos/dados-v1/migrar.fé'),str(p)],env=BASE_ENV,capture_output=True,timeout=40)
    if r.returncode:
     (self.lab/'falha-migracao.log').write_bytes(r.stderr);raise RuntimeError('migração léxica privada recusada')
    p.write_bytes(r.stdout);migration.append({'arquivo':str(p.relative_to(cand)),'antes':old,'depois':sha(p),'avisos_nulo':r.stderr.count(b'REVISAR')})
  # Bibliotecas genéricas migradas e ensaiadas no candidato base.
  bib=cand/'local/share/santafé/3.0/bibf';bib.mkdir(parents=True,exist_ok=True)
  shutil.copytree(self.stage/'bibs/bibf',bib,dirs_exist_ok=True)
  for lib in ('arquivo','rede','segredo','mariadb','tomada'):
   source=self.stage/f'bibs/bibc/{lib}/{lib}.so';ensure(source.is_file(),'DSO candidato ausente')
   target=cand/f'local/lib/santafé/3.0/bibc/{lib}.so'; target.parent.mkdir(parents=True,exist_ok=True)
   shutil.copyfile(source,target)
  for n in ('santafé','santafec'):
   shutil.copy2(self.stage/'src'/n,cand/'local/bin'/n)
  # Migrar também SDK, auxiliares SLS/CLI e inicializador. Não misturar DSO 2.1/3.
  for part in ('bin','sls','pacotes','c','fe','pc'):
   self.run(['bash',self.stage/'ferramentas/instalar-arquivos.sh',part,cand/'local','linux','3.0.0-rc.1'],cwd=self.stage)
  for app in ('correio','carteiro'):
   for p in (self.stage/'aplicativos'/app).rglob('*.fé'):
    rel=p.relative_to(self.stage/'aplicativos'/app);dst=cand/'opt'/app/rel
    if dst.is_file():shutil.copyfile(p,dst)
  self.adjust_operational(cand)
  for kind in ('estavel','candidata'):
   g=self.lab/kind
   for p in (g/'etc/nginx').rglob('*'):
    if not p.is_file():continue
    try:text=p.read_text()
    except UnicodeDecodeError:continue
    text=re.sub(r'(?m)^\s*user\s+[^;]+;', 'user root;',text)
    text=re.sub(r'(ssl_certificate\s+)[^;]+;',r'\1/tmp/tls-certificado.pem;',text)
    text=re.sub(r'(ssl_certificate_key\s+)[^;]+;',r'\1/tmp/tls-chave.pem;',text)
    text=re.sub(r'(?m)^\s*ssl_dhparam\s+[^;]+;', '# DH de produção não copiado; TLS ECDHE de ensaio.',text)
    for old,new in ((7000,17000),(7100,17100),(7101,17101),(7200,17200)):
     text=text.replace('127.0.0.1:'+str(old),'127.0.0.1:'+str(new))
    p.write_text(text)
   for folder in ('var/log/nginx','var/cache/nginx'):(g/folder).mkdir(parents=True,exist_ok=True)
   (g/'etc/letsencrypt').mkdir(exist_ok=True)
   (g/'etc/letsencrypt/options-ssl-nginx.conf').write_text('ssl_protocols TLSv1.2 TLSv1.3;\n')
  compiled=0
  for tree in ('opt','etc','local/share'):
   for p in sorted((cand/tree).rglob('*.fé')):
    result=subprocess.run([str(cand/'local/bin/santafec'),'-p',str(p)],env=BASE_ENV,capture_output=True,timeout=40)
    if result.returncode:
     (self.lab/'falha-compilacao.log').write_bytes(result.stderr);raise RuntimeError('fonte da réplica candidata não compila')
    compiled+=1
  write(self.lab/'migracao-fontes.json',migration)
  self.passed('cópia privada e migração léxica',arquivos_capturados=len(m['arquivos']),fontes=len(migration),compilados=compiled,avisos_nulo=sum(x['avisos_nulo'] for x in migration))
 def mount(self,g):
  # Todas as montagens pertencem ao namespace transitório deste processo.
  for name in ('usr','bin','sbin','lib','lib64'):
   src=Path('/')/name
   if src.exists():
    self.run(['mount','--bind',src,g/name]);self.run(['mount','-o','remount,bind,ro',g/name])
  self.run(['mount','--bind',g/'local',g/'usr/local'])
  self.run(['mount','-o','remount,bind,ro',g/'usr/local'])
  self.run(['mount','--bind',self.lab/'estado-lib',g/'var/lib'])
  self.run(['mount','--bind',self.root/'var/www',g/'var/www'])
  self.run(['mount','-o','remount,bind,ro',g/'var/www'])
  for n in ('null','zero','random','urandom'):self.run(['mount','--bind','/dev/'+n,g/'dev'/n])
  self.run(['mount','-t','proc','proc',g/'proc'])
 def database(self):
  (self.lab/'temporarios-db12').mkdir(mode=0o700,exist_ok=True)
  shutil.copytree(self.a.restauro/'dados',self.lab/'dados')
  (self.lab/'exportacao').mkdir();(self.lab/'sem-plugins').mkdir()
  self.dbport=13306
  p=self.start('banco',[shutil.which('mariadbd') or '/usr/sbin/mariadbd','--no-defaults','--user=root','--tmpdir='+str(self.lab/'temporarios-db12'),'--datadir='+str(self.lab/'dados'),'--socket='+str(self.lab/'b.sock'),'--pid-file='+str(self.lab/'pid'),'--bind-address=127.0.0.1','--port='+str(self.dbport),'--skip-log-bin','--event-scheduler=DISABLED','--local-infile=0','--skip-symbolic-links','--secure-file-priv='+str(self.lab/'exportacao'),'--plugin-dir='+str(self.lab/'sem-plugins'),'--innodb-buffer-pool-size=64M','--innodb-log-file-size=16M'])
  self.wait(p,self.dbport)
  baseline=json.loads((self.a.restauro/'baseline.json').read_text())['tabelas'];actual=self.tables()
  ensure(all(actual[db][t]==[v['linhas'],v['checksum']] for db in DBS for t,v in baseline[db].items()),'baseline restaurada divergiu')
  self.baseline=actual;write(self.lab/'baseline-aplicativos.json',actual)
  for prefix,db in zip(('sfensaio','pdcensaio'),DBS):
   self.sql("CREATE USER "+quote(prefix)+"@'127.0.0.1' IDENTIFIED BY 'somente-replica-11'; GRANT ALL ON "+ident(db)+".* TO "+quote(prefix)+"@'127.0.0.1';")
  self.passed('bancos clonados e objetos íntegros',**self.objects())
 def env_unit(self,g,unit):
  env=dict(BASE_ENV);env['PATH']='/usr/local/bin:/usr/bin:/bin'
  paths=[]
  for base in ('etc/systemd/system','usr/lib/systemd/system'):
   f=g/base/unit
   if f.is_file():paths.append(f)
  paths+=sorted((g/'etc/systemd/system'/(unit+'.d')).glob('*.conf'))
  for p in paths:
   for line in p.read_text().splitlines():
    if line.startswith('EnvironmentFile='):
     name=line.split('=',1)[1].strip().strip('"').lstrip('-');file=g/name.lstrip('/')
     if file.is_file():
      for row in file.read_text().splitlines():
       if not row.strip() or row.lstrip().startswith('#') or '=' not in row:continue
       k,v=row.split('=',1);k=k.strip();v=v.strip()
       if v[:1] in ('"',"'"):
        parts=shlex.split(v,posix=True);ensure(len(parts)==1,'ambiente multilinha exige revisão');v=parts[0]
       ensure(re.fullmatch('[A-Za-z_][A-Za-z_0-9]*',k),'nome de ambiente inválido');env[k]=v
    elif line.startswith('Environment='):
     for pair in shlex.split(line.split('=',1)[1]):
      k,v=pair.split('=',1);env[k]=v
  # Nenhuma credencial operacional chega ao processo de ensaio.
  for k in list(env):
   if re.search('SENHA|PASSWORD|TOKEN|SECRET|MAILJET',k):env.pop(k)
  for prefix,user,db in zip(('SANTAFE','PAODOCAFE'),('sfensaio','pdcensaio'),DBS):
   for key,val in {'HOST':'127.0.0.1','PORTA':str(self.dbport),'USUARIO':user,'SENHA':'somente-replica-11','BANCO':db}.items():env[prefix+'_MARIADB_'+key]=val
  pdc=unit in ('carteiro-paodocafe.service','correio-envios-paodocafe.service')
  env.update(LUA_PATH='/usr/local/share/santafé/1.0/bibf/?.fé;/usr/local/share/santafé/1.0/bibf/?/?.fé',LUA_CPATH='/usr/local/lib/santafé/1.0/bibc/?.so',
    CORREIO_RAIZ='/opt/correio',CARTEIRO_RAIZ='/opt/carteiro',PAODOCAFE_RAIZ='/opt/paodocafe',
    CORREIO_BANCO_PREFIXO='PAODOCAFE' if pdc else 'SANTAFE',CORREIO_DOMINIO=DOMS[int(pdc)],CORREIO_DOMINIOS_LOCAIS=','.join(DOMS),
    CORREIO_DEPOSITO=DEPS[int(pdc)],CORREIO_BANCOS_ADICIONAIS='' if pdc else DOMS[1]+'|PAODOCAFE|'+DEPS[1],
    CORREIO_AUTENTICACAO_ATIVA='falso',CORREIO_ANTIVIRUS_ATIVO='falso',CORREIO_TRIAGEM_ATIVA='falso',CORREIO_DKIM_EXIGIR='falso',CORREIO_DKIM_IDENTIDADES='',
    CORREIO_RECEBEDOR_ENDERECO='127.0.0.1',CORREIO_RECEBEDOR_PORTA='11025',CORREIO_RECEBEDOR_NOME='localhost',
    CORREIO_AGENCIA_ENDERECO='127.0.0.1',CORREIO_AGENCIA_PORTA_STARTTLS='11587',CORREIO_AGENCIA_PORTA_TLS='11465',CORREIO_AGENCIA_NOME='localhost',
    CORREIO_AGENCIA_CERTIFICADO='/tmp/tls-certificado.pem',CORREIO_AGENCIA_CHAVE='/tmp/tls-chave.pem',
    CORREIO_IMAP_ENDERECO='127.0.0.1',CORREIO_IMAP_PORTA='11993',CORREIO_IMAP_CERTIFICADO='/tmp/tls-certificado.pem',CORREIO_IMAP_CHAVE='/tmp/tls-chave.pem',
    CARTEIRO_ENDERECO='127.0.0.1',CARTEIRO_PORTA='17101' if pdc else '17100',PAODOCAFE_ENDERECO='127.0.0.1',PAODOCAFE_PORTA='17200',SANTAFE_PORTA='17000',
    CORREIO_ENVIOS_MODO='retransmissor',CORREIO_ENVIOS_ENDERECO='127.0.0.1',CORREIO_ENVIOS_PORTA='11025',CORREIO_ENVIOS_SEGURANCA='nenhuma',CORREIO_ENVIOS_USUARIO='',CORREIO_ENVIOS_SENHA='')
  # Assinaturas de saída privadas são desativadas; DNSSEC será ensaiado à parte.
  for key in ('CORREIO_DKIM_CHAVE','CORREIO_DKIM_SELETOR','CORREIO_ENVIOS_USUARIO','CORREIO_ENVIOS_SENHA'):env.pop(key,None)
  return env
 def command(self,g,code=None,entry=None):
  cmd=['/usr/sbin/chroot',str(g),'/usr/local/bin/santafé','-P']
  if code is not None:cmd+=['-e',code]
  if entry:cmd+=['/opt/'+entry]
  return cmd
 def sf(self,kind,code):
  g=self.lab/kind;env=self.env_unit(g,'carteiro.service')
  r=subprocess.run(self.command(g,code),env=env,capture_output=True,timeout=40)
  if r.returncode:
   (self.lab/'falha-sf.log').write_bytes(r.stderr);raise RuntimeError('utilitário privado Santafé falhou')
  return r.stdout.decode().strip()
 def setup_users(self):
  self.password='ensaio-apenas-replica-11';self.user='réplica11'
  h=self.sf('estavel','local s=importe "segredo"; local r=importe "rede"; s.protejaSenhaAssíncrono("'+self.password+'",função(h,f) garanta(h,f); mostre(h); r.pareLaço() fim); r.laço()')
  ensure(h.startswith('$argon2id$'),'hash de teste inválido');self.tokens={};self.owners={}
  for i,db in enumerate(DBS):
   self.sql('INSERT INTO usuarios (nome,usuario,email,senha_hash) VALUES ("Réplica isolada",'+quote(self.user)+','+quote(self.user+'@'+DISPLAYDOMS[i])+','+quote(h)+');',db)
   uid=int(self.sql('SELECT id FROM usuarios WHERE usuario='+quote(self.user)+';',db))
   self.sql('INSERT INTO correio_caixas (usuario_id,parte_local,dominio_ascii,endereco_exibido,nome_exibido) VALUES ('+str(uid)+','+quote(self.user)+','+quote(DOMS[i])+','+quote(self.user+'@'+DISPLAYDOMS[i])+',"Réplica isolada");',db)
   users=[int(x) for x in self.sql('SELECT DISTINCT usuario_id FROM correio_caixas ORDER BY usuario_id;',db).splitlines()]
   self.owners[db]=uid
   for owner in users:
    token='replica11-'+str(i)+'-'+str(owner);digest=self.sf('estavel','mostre((importe "segredo").resumaBilhete('+json.dumps(token)+'))')
    self.sql('INSERT INTO sessoes(usuario_id,token_hash,csrf_token,expira_em) VALUES ('+str(owner)+','+quote(digest)+',"replica11-csrf",DATE_ADD(NOW(),INTERVAL 1 DAY));',db)
    self.tokens[(db,owner)]=token
  self.passed('contas sintéticas e sessões somente nos clones',contas=2,sessoes=len(self.tokens))
 def http(self,port,path,token=None,fields=None):
  c=http.client.HTTPConnection('127.0.0.1',port,timeout=15)
  headers={'Cookie':'sf_sessao='+token} if token else {};body=None
  if fields is not None:body=urllib.parse.urlencode(fields);headers['Content-Type']='application/x-www-form-urlencoded'
  c.request('POST' if fields is not None else 'GET',urllib.parse.quote(path,safe='/%?=&'),body,headers)
  r=c.getresponse();data=r.read();status=r.status;c.close()
  if status>=400:
   with (self.lab/'http-status.jsonl').open('a') as log:log.write(json.dumps({'porta':port,'rota':path,'status':status,'resumo':hashlib.sha256(data).hexdigest()})+'\n')
   (self.lab/'http-falha.bin').write_bytes(data)
  return status,data
 def services(self,kind):
  g=self.lab/kind;procs=[]
  for unit,entry,port in [('sfdev.service','sfdev.fé',17000),('paodocafe.service','paodocafe/paodocafe.fé',17200),('carteiro.service','carteiro/carteiro.fé',17100),('carteiro-paodocafe.service','carteiro/carteiro.fé',17101),('correio-recebedor.service','correio/recebedor.fé',11025),('correio-agencia.service','correio/agência.fé',11587),('correio-imap.service','correio/imap.fé',11993)]:
   p=self.start(kind+'-'+unit,self.command(g,entry=entry),self.env_unit(g,unit),g/'opt');procs.append(p)
   try:self.wait(p,port)
   except Exception:raise RuntimeError(kind+': falhou inicialização de '+unit)
  for port,path in ((17100,'/carteiro/estado'),(17101,'/carteiro/estado'),(17200,'/estado')):
   for _ in range(200):
    status,body=self.http(port,path)
    if status==200:break
    time.sleep(.1)
   else:
    (self.lab/'http-falha.bin').write_bytes(body);raise RuntimeError(kind+': prontidão HTTP falhou '+str(port))
  return procs
 def infrastructure(self,kind):
  g=self.lab/kind
  (self.lab/'estado-lib/nginx').mkdir(exist_ok=True)
  nginx=self.start(kind+'-nginx',['/usr/sbin/chroot',str(g),'/usr/sbin/nginx','-g','daemon off;'],BASE_ENV,g/'opt')
  self.wait(nginx,443)
  ctx=ssl.create_default_context(cafile=str(self.stage/'testes/recursos/tls-local-certificado.pem'))
  for domain in DOMS:
   for path in ('/','/carteiro/estado'):
    c=http.client.HTTPSConnection('127.0.0.1',443,context=ctx,timeout=10)
    c.request('GET',path,headers={'Host':domain});r=c.getresponse();body=r.read();status=r.status;c.close()
    if status!=200:(self.lab/'proxy-falha.bin').write_bytes(body)
    ensure(status==200,'proxy HTTPS da réplica: '+str(status))
  self.passed(kind+': nginx capturado, TLS de teste e proxy dos dois domínios',requisicoes=4)
  env=self.env_unit(g,'nomes-autoridade.service')
  env.update(NOMES_AUTORIDADE_ENDERECO='127.0.0.1',NOMES_AUTORIDADE_PORTA='15353',DNS_AUTORITATIVO_ENDERECO='127.0.0.1',DNS_AUTORITATIVO_PORTA='15353')
  dns=self.start(kind+'-dns',self.command(g,entry='santafe-nomes/autoridade.fé'),env,g/'opt');self.wait(dns,15353)
  zonefile=env.get('NOMES_ZONAS_ARQUIVO','/etc/santafe-nomes/zonas.fé')
  code='local d=executeArquivo('+json.dumps(zonefile,ensure_ascii=False)+'); local saida='+('[]' if kind=='candidata' else '{}')+'; para _,z em ipares(d.zonas ou d) início saida[#saida+1]={nome=z.nome,assinada=z.dnssec e verdadeiro ou falso} fim; mostre(json.cod(saida))'
  zones=json.loads(self.sf(kind,code));ensure(zones,'zonas DNS ausentes')
  signatures=0;keys={}
  for zone in zones:
   for protocol in ('+tcp','+notcp'):
    result=self.run(['dig','@127.0.0.1','-p','15353',zone['nome'],'SOA','+dnssec',protocol,'+noall','+comments','+answer','+time=2','+tries=1']).decode()
    ensure('status: NOERROR' in result and re.search(r'\sSOA\s',result),'resposta SOA da réplica')
    if zone['assinada']:ensure('RRSIG' in result,'RRSIG ausente');signatures+=1
   if zone['assinada']:
    key=self.run(['dig','@127.0.0.1','-p','15353',zone['nome'],'DNSKEY','+short','+time=2','+tries=1'])
    ensure(key.strip(),'DNSKEY ausente');keys[zone['nome']]=hashlib.sha256(key).hexdigest()
  if hasattr(self,'dnskeys'):ensure(keys==self.dnskeys,'migração alterou identidades DNSSEC')
  else:self.dnskeys=keys
  self.passed(kind+': zonas DNS reais em UDP/TCP e chaves DNSSEC preservadas',zonas=len(zones),respostas_assinadas=signatures)
  return [nginx,dns]
 def read_all(self,kind):
  summary={'originais':0,'anexos':0,'paginas':0}
  status,_=self.http(17000,'/entrar')
  ensure(status==(200 if kind=='candidata' else 500),'regressão do destino opcional no portal')
  summary['entrada_sem_destino_http']=status
  for port,paths in ((17000,('/','/baixar','/cadastro','/entrar?destino=/comunidade','/comunidade')),(17200,('/','/entrar','/primeiro-acesso','/cadastro'))):
   for path in paths:
    status,data=self.http(port,path);ensure(status==200 or(port==17200 and path=='/cadastro' and status in (303,404)),kind+': página pública falhou '+str(port)+path+' status='+str(status))
    summary['paginas']+=1
  for i,db in enumerate(DBS):
   port=17100+i
   for (database,owner),token in self.tokens.items():
    if database!=db:continue
    for folder in ('entrada','enviadas','rascunhos','lixeira','todas'):
     status,data=self.http(port,'/carteiro/'+folder,token)
     if status!=200:(self.lab/'http-falha.bin').write_bytes(data)
     ensure(status==200,kind+': caixa retornou '+str(status));summary['paginas']+=1
   rows=self.sql('SELECT c.id,c.mime_objeto,b.usuario_id FROM correio_cartas c JOIN correio_caixas b ON b.id=c.caixa_id ORDER BY c.id;',db)
   for line in rows.splitlines():
    mid,digest,owner=line.split('\t');token=self.tokens[(db,int(owner))]
    status,body=self.http(port,'/carteiro/mensagens/'+mid+'/original',token)
    ensure(status==200 and hashlib.blake2b(body,digest_size=32).hexdigest()==digest,kind+': MIME histórico divergiu');summary['originais']+=1
   rows=self.sql('SELECT a.id,a.carta_id,a.dados_objeto,b.usuario_id FROM correio_anexos a JOIN correio_cartas c ON c.id=a.carta_id JOIN correio_caixas b ON b.id=c.caixa_id ORDER BY a.id;',db)
   for line in rows.splitlines():
    aid,mid,digest,owner=line.split('\t');token=self.tokens[(db,int(owner))]
    status,body=self.http(port,'/carteiro/mensagens/'+mid+'/anexos/'+aid,token)
    ensure(status==200 and hashlib.blake2b(body,digest_size=32).hexdigest()==digest,kind+': anexo histórico divergiu');summary['anexos']+=1
  self.passed(kind+': leitura dos aplicativos e conteúdo integral',**summary)
 def message(self,phase,i):
  msg=EmailMessage(policy=email.policy.SMTPUTF8);msg['From']='Homologação <origem@ensaio.invalid>';msg['To']=self.user+'@'+DOMS[i]
  msg['Subject']='Réplica11 '+phase;msg['Message-ID']='<replica11-'+phase+'-'+str(i)+'@ensaio.invalid>'
  msg.set_content('Escrita de ensaio: acentos, nulo e lista.');msg.add_attachment(b'%PDF-1.7\nreplica11\n',maintype='application',subtype='pdf',filename='validação.pdf')
  with smtplib.SMTP('127.0.0.1',11025,timeout=20) as smtp:
   smtp.ehlo();ensure(not smtp.sendmail('origem@ensaio.invalid',[self.user+'@'+DOMS[i]],msg.as_bytes(),mail_options=['SMTPUTF8','BODY=8BITMIME']),'recepção recusou ensaio')
 def installed(self):
  g=self.lab/'candidata';env=self.env_unit(g,'carteiro.service')
  rootcmd=['/usr/sbin/chroot',str(g)]
  r=subprocess.run(rootcmd+['/usr/local/bin/santafé','instale','--ajuda'],env=env,capture_output=True,timeout=20)
  ensure(r.returncode==0 and b'instale' in r.stdout,'CLI instalada na réplica')
  (g/'tmp/projeto').mkdir(exist_ok=True)
  requests=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'processId':None,'rootUri':'file:///tmp/projeto','capabilities':{}}},
            {'jsonrpc':'2.0','method':'initialized','params':{}},
            {'jsonrpc':'2.0','id':2,'method':'shutdown','params':None},
            {'jsonrpc':'2.0','method':'exit','params':None}]
  wire=b''
  for req in requests:
   body=json.dumps(req).encode();wire+=b'Content-Length: '+str(len(body)).encode()+b'\r\n\r\n'+body
  r=subprocess.run(rootcmd+['/usr/local/bin/santafé-sls'],input=wire,env=env,capture_output=True,timeout=20)
  if r.returncode:(self.lab/'sls-falha.log').write_bytes(r.stderr)
  ensure(r.returncode==0,'SLS instalado não concluiu ciclo LSP')
  data=r.stdout;responses=[]
  while data:
   head,data=data.split(b'\r\n\r\n',1);n=int(re.search(rb'Content-Length:\s*(\d+)',head).group(1));responses.append(json.loads(data[:n]));data=data[n:]
  init=next(x['result'] for x in responses if x.get('id')==1)
  ensure(init['serverInfo']['version']=='1.1.0-rc.1','versão SLS instalada')
  ensure(init['capabilities']['textDocumentSync']['change']==2,'sincronização incremental instalada')
  ensure('#define SANTAFE_ABI_MAJOR 3' in (g/'local/include/lua.h').read_text(),'SDK IBA3 instalado')
  ensure('Version: 3.0.0-rc.1' in (g/'local/lib/pkgconfig/santafe.pc').read_text(),'pkg-config instalado')
  self.passed('SLS, CLI e SDK da geração candidata instalados no chroot',sls='1.1.0-rc.1',iba=3)
 def protocols(self,kind,phase):
  ctx=ssl.create_default_context(cafile=str(self.stage/'testes/recursos/tls-local-certificado.pem'))
  g=self.lab/kind
  for i,db in enumerate(DBS):
   address=self.user+'@'+DOMS[i];token=self.tokens[(db,self.owners[db])]
   # As filas históricas permanecem guardadas, com prazo apenas no clone.
   old=[x.split('\t') for x in self.sql('SELECT id,proxima_tentativa FROM correio_fila ORDER BY id;',db).splitlines()]
   self.sql('UPDATE correio_fila SET proxima_tentativa=UNIX_TIMESTAMP()+31536000;',db)
   msg=EmailMessage(policy=email.policy.SMTPUTF8);msg['From']=address;msg['To']=address
   msg['Subject']='Agência réplica11 '+phase;msg.set_content('Envio isolado e reversível.')
   sasl=base64.b64encode(('\0'+address+'\0'+self.password).encode()).decode()
   with smtplib.SMTP('127.0.0.1',11587,timeout=20) as smtp:
    smtp.ehlo();smtp.starttls(context=ctx);smtp.ehlo()
    ensure(smtp.has_extn('SMTPUTF8') and smtp.docmd('AUTH','PLAIN '+sasl)[0]==235,'AUTH/SMTPUTF8')
    ensure(not smtp.sendmail(address,[address],msg.as_bytes(),mail_options=['SMTPUTF8','BODY=8BITMIME']),'submissão privada falhou')
   status,_=self.http(17100+i,'/carteiro/enviar',token,{'csrf':'replica11-csrf','para':address,'assunto':'Compositor réplica11 '+phase,'texto':'Carta criada durante a migração.'})
   ensure(status in (302,303),'compositor HTTP falhou')
   unit='correio-envios-paodocafe.service' if i else 'correio-envios.service'
   for tentativa in range(2):
    proc=self.start(kind+'-fila-'+str(i)+'-'+phase+'-'+str(tentativa),self.command(g,entry='correio/envios.fé'),self.env_unit(g,unit),g/'opt')
    ensure(proc.wait(timeout=40)==0,'processador privado de fila falhou')
   last=max([int(row[0]) for row in old] or [0])
   states=self.sql('SELECT estado FROM correio_fila WHERE id>'+str(last)+';',db).splitlines()
   ensure(len(states)==2 and set(states)=={'entregue'},'novas cartas: '+str(len(states))+'; estados='+','.join(sorted(set(states))))
   for mid,when in old:self.sql('UPDATE correio_fila SET proxima_tentativa='+str(int(when))+' WHERE id='+str(int(mid))+';',db)
   with imaplib.IMAP4_SSL('127.0.0.1',11993,ssl_context=ctx,timeout=20) as imap:
    imap.authenticate('PLAIN',lambda _: ('\0'+address+'\0'+self.password).encode())
    ensure(imap.select('INBOX')[0]=='OK','seleção IMAP')
    typ,data=imap.uid('SEARCH',None,'ALL');ensure(typ=='OK' and data[0],'busca IMAP')
    uid=data[0].split()[0];typ,data=imap.uid('FETCH',uid,'(BODY.PEEK[])')
    ensure(typ=='OK' and any(isinstance(x,tuple) and b'R\xc3\xa9plica11' in x[1] for x in data),'leitura IMAP do MIME')
    ensure(imap.uid('COPY',uid,'Lixeira')[0]=='OK','UID COPY')
    ensure(imap.response('COPYUID')[1][0] is not None,'COPYUID ausente')
    ensure(imap.select('Lixeira')[0]=='OK','Lixeira IMAP')
    ensure(imap.store('1','+FLAGS',r'(\Deleted)')[0]=='OK' and imap.expunge()[0]=='OK','exclusão cópia IMAP')
    ensure(imap.append('Rascunhos',None,None,msg.as_bytes())[0]=='OK','APPEND')
   # Login dos aplicativos usa apenas a conta sintética, sem alterar senhas reais.
   status,_=self.http(17200 if i else 17000,'/entrar',fields={('usuario' if i else 'usuário'):self.user,'senha':self.password,'destino':'/carteiro/'})
   ensure(status in (302,303),'login web da réplica domínio '+str(i)+' status '+str(status))
  self.passed(kind+': SMTP TLS, filas, compositor, login e IMAP nos dois bancos',fase=phase)
 def load(self):
  duration=int(os.environ.get('SANTAFE_REPLICA_CARGA_SEGUNDOS','60'))
  ensure(60<=duration<=600,'duração da carga inválida')
  start=time.monotonic();deadline=start+duration
  def worker(i):
   db=DBS[i%2];port=17100+i%2;tokens=[t for (d,u),t in self.tokens.items() if d==db]
   n=0
   while time.monotonic()<deadline:
    token=tokens[n%len(tokens)];status,body=self.http(port,'/carteiro/entrada',token)
    ensure(status==200,'carga HTTP retornou '+str(status));n+=1
   return n
  with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:counts=list(pool.map(worker,range(6)))
  self.passed('carga da réplica candidata',segundos=round(time.monotonic()-start,2),operacoes=sum(counts),clientes=6)
 def execute(self):
  self.prepare()
  for kind in ('estavel','candidata'):self.mount(self.lab/kind)
  self.database();self.setup_users()
  self.installed()
  for kind,phase in (('estavel','antes'),('candidata','depois'),('estavel','rollback')):
   before=self.tables();procs=self.services(kind)
   procs+=self.infrastructure(kind)
   ensure(self.tables()==before,'inicialização alterou dados persistidos')
   self.read_all(kind)
   for i in range(2):self.message(phase,i)
   self.protocols(kind,phase)
   if kind=='candidata':self.load()
   self.read_all(kind);self.objects()
   self.stop(procs)
   self.passed(kind+': reinício sem alteração e novas escritas preservadas',fase=phase)
  self.report['resultado']='PASSOU';self.report['limites']=['TLS local de teste; sem conexão externa','Antivírus, triagem e autenticação DNS externa desativados neste percurso','Estáticos montados somente para leitura; upload de comunidade não ensaiado','Não é ainda soak prolongado; DNSSEC local não revalida delegação pública']

def main():
 p=argparse.ArgumentParser();p.add_argument('replica',type=Path);p.add_argument('restauro',type=Path);p.add_argument('candidato',type=Path);p.add_argument('--interior',action='store_true');p.add_argument('--lab',type=Path);a=p.parse_args()
 ensure(sys.platform=='linux','exige Linux');V.conferir(a.replica)
 ensure((a.restauro/'GATE_RESTAURACAO_OK').is_file() and str(a.restauro).startswith('/var/tmp/santafe-restauro11-'),'restauro privado não validado')
 if not a.interior:
  os.umask(0o077);lab=Path(tempfile.mkdtemp(prefix='santafe-migracao11-',dir='/var/tmp'))
  env=dict(BASE_ENV,SANTAFE_NET_ORIGEM=os.readlink('/proc/self/ns/net'))
  cmd=['unshare','--user','--map-root-user','--mount','--net','--pid','--fork',sys.executable,str(Path(__file__).resolve()),str(a.replica),str(a.restauro),str(a.candidato),'--interior','--lab',str(lab)]
  result=subprocess.call(cmd,env=env);print('LABORATORIO_PRIVADO',lab,'codigo',result);raise SystemExit(result)
 ensure(os.environ.get('SANTAFE_NET_ORIGEM') and os.readlink('/proc/self/ns/net')!=os.environ['SANTAFE_NET_ORIGEM'],'namespace não isolado')
 ensure(os.getpid()==1,'namespace PID obrigatório')
 ensure({x['ifname'] for x in json.loads(subprocess.check_output(['ip','-j','link']))}=={'lo'},'rede externa presente')
 subprocess.run(['ip','link','set','lo','up'],check=True)
 ensure(not subprocess.check_output(['ip','route','show','default']).strip(),'rota externa presente')
 os.umask(0o077);lab=Replica(a)
 try:lab.execute()
 except Exception as e:
  message=str(e) if type(e) is RuntimeError else type(e).__name__+' no ensaio; detalhe no registro privado'
  lab.report['resultado']='FALHOU';lab.report['falha']=message
  try:(lab.lab/'rastro-privado.txt').write_text(traceback.format_exc())
  except OSError:pass
  print('FALHOU',message,flush=True)
 finally:
  lab.stop(lab.procs)
  for h in lab.handles:h.close()
  try:write(lab.lab/'resultado.json',lab.report)
  except OSError:print('Não foi possível gravar resultado; ensaio NÃO aprovado',flush=True);lab.report['resultado']='FALHOU'
 if lab.report['resultado']!='PASSOU':raise SystemExit(1)
if __name__=='__main__':main()
