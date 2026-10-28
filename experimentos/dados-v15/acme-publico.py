#!/usr/bin/env python3
"""Emissão pública isolada. Nunca instala certificados ou administra serviços."""
from pathlib import Path
import argparse,configparser,fcntl,hashlib,json,os,re,shlex,shutil,signal,ssl,stat,subprocess,sys,tempfile,time,urllib.request
DOMAIN='xn--podocaf-xwa4d.com.br'
WEB=Path('/var/www/paodocafe.com.br')
LE=Path('/etc/letsencrypt')
SERVER='https://acme-v02.api.letsencrypt.org/directory'
TRUST='/etc/ssl/certs/ca-certificates.crt'
ENV={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LANG':'C.UTF-8','GSETTINGS_BACKEND':'memory'}
TOKEN=re.compile(r'[A-Za-z0-9_-]{20,200}\Z')
def need(v,msg):
 if not v:raise RuntimeError(msg)
def digest(data):return hashlib.sha256(data).hexdigest()
def save(p,x):
 tmp=p.with_suffix('.novo');tmp.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n');os.replace(tmp,p)
def read(p):return json.loads(p.read_text())
def no_links(p):
 for q in [p,*p.parents]:need(not q.is_symlink(),'link recusado: '+str(q))
def regular(p):
 no_links(p);need(p.is_file(),'arquivo ausente: '+str(p));return p.read_bytes()
def clean_token(lab,record):
 """Só remove o arquivo criado por este ensaio, com mesmo inode e conteúdo."""
 r=read(record);p=Path(r['arquivo']);no_links(p)
 if p.exists():
  s=p.stat();need(s.st_ino==r['inode'] and s.st_dev==r['device'] and digest(p.read_bytes())==r['sha256'],'desafio modificado; preservado para revisão')
  p.unlink()
 r['limpo']=True;save(record,r)
def hook(lab,action):
 state=read(lab/'contexto.json');token=os.environ.get('CERTBOT_TOKEN','');domain=os.environ.get('CERTBOT_DOMAIN','')
 need(TOKEN.fullmatch(token) and domain==state['dominio'],'desafio fora do domínio/alfabeto permitido')
 record=lab/'tokens'/(token+'.json')
 if action=='limpar':
  if record.exists():clean_token(lab,record)
  return
 value=os.environ.get('CERTBOT_VALIDATION','');need(re.fullmatch(r'[A-Za-z0-9_.-]{20,500}',value),'valor inválido')
 directory=Path(state['desafios']);no_links(directory);need(directory.is_dir(),'diretório ausente')
 need(not record.exists(),'token repetido')
 p=directory/token;fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o644)
 try:
  os.fchmod(fd,0o644);data=value.encode('ascii');os.write(fd,data);os.fsync(fd);s=os.fstat(fd)
 finally:os.close(fd)
 save(record,{'arquivo':str(p),'inode':s.st_ino,'device':s.st_dev,'sha256':digest(data),'limpo':False,'http_conferido':False})
 try:
  url=state['origem_http']+'/.well-known/acme-challenge/'+token
  with urllib.request.urlopen(url,timeout=20) as response:
   need(response.status==200 and response.read(1024)==data,'desafio não corresponde à resposta HTTP pública')
  r=read(record);r['http_conferido']=True;save(record,r)
 except BaseException:
  clean_token(lab,record);raise

def command(lab,account,renew=False):
 # -c evita carregar /etc/letsencrypt/cli.ini e hooks configurados pela instalação.
 base=['/usr/bin/certbot','-c',str(lab/'vazio.ini'),'--config-dir',str(lab/'config'),'--work-dir',str(lab/'work'),'--logs-dir',str(lab/'logs'),'--server',SERVER,'--non-interactive','--no-directory-hooks','--no-eff-email','--account',account]
 if renew:return base+['renew','--cert-name','ensaio-dados15','--force-renewal','--no-random-sleep-on-renew']
 auth=shlex.join(['/usr/bin/python3',str(lab/'roteiro.py'),'--hook',str(lab),'autorizar'])
 cleanup=shlex.join(['/usr/bin/python3',str(lab/'roteiro.py'),'--hook',str(lab),'limpar'])
 return base+['certonly','--manual','--preferred-challenges','http','--manual-auth-hook',auth,'--manual-cleanup-hook',cleanup,'--cert-name','ensaio-dados15','-d',DOMAIN]

def run(lab,label,argv,timeout=240):
 with (lab/(label+'.log')).open('wb') as log:
  p=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=log,stderr=log,env=ENV,cwd=lab,start_new_session=True)
  try:code=p.wait(timeout=timeout)
  except BaseException:
   os.killpg(p.pid,signal.SIGTERM)
   try:p.wait(timeout=10)
   except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
   raise
 need(code==0,label+' falhou; diagnóstico privado: '+str(lab/(label+'.log')))

def hashes(root):
 return {str(p.relative_to(root)):digest(p.read_bytes()) for p in sorted(root.rglob('*')) if p.is_file()}
def snapshot():
 units=['nginx.service','sfdev.service','paodocafe.service','carteiro.service','carteiro-paodocafe.service','correio-imap.service','correio-agencia.service','correio-recebedor.service']
 status=subprocess.check_output(['systemctl','show','--property=Id,MainPID,ActiveEnterTimestampMonotonic',*units],env=ENV)
 need(status.count(b'MainPID=')==8 and b'MainPID=0\n' not in status,'serviço necessário inativo')
 certs={}
 for domain in ['xn--santaf-gva.dev.br',DOMAIN]:
  import socket
  with socket.create_connection((domain,443),timeout=15) as raw,ssl.create_default_context().wrap_socket(raw,server_hostname=domain) as tls:certs[domain]=digest(tls.getpeercert(True))
  for route in ['/','/carteiro/']:
   with urllib.request.urlopen('https://'+domain+route,timeout=20) as f:need(f.status==200,'HTTPS de produção falhou')
 return {'servicos':digest(status),'nginx':hashes(Path('/etc/nginx')),'letsencrypt':hashes(LE),'nucleo':digest(Path('/usr/local/bin/santafé').read_bytes()),'certificados_servidos':certs}
def choose_account():
 cfg=configparser.ConfigParser(interpolation=None);cfg.read_string('[principal]\n'+regular(LE/'renewal'/ (DOMAIN+'.conf')).decode())
 account=cfg['renewalparams'].get('account','');server=cfg['renewalparams'].get('server','')
 need(re.fullmatch('[0-9a-f]{32}',account) and server==SERVER,'conta/servidor de renovação não correspondem')
 path=LE/'accounts/acme-v02.api.letsencrypt.org/directory'/account
 for name in ['regr.json','meta.json','private_key.json']:regular(path/name)
 reg=read(path/'regr.json');need(reg['body'].get('status')=='valid' and reg['uri'].startswith('https://acme-v02.api.letsencrypt.org/acme/acct/'),'conta ACME não está válida')
 return account,path

def inspect_cert(lab):
 live=lab/'config/live/ensaio-dados15'
 # Links do Certbot são aceitos somente dentro de archive privado.
 for name in ['cert.pem','chain.pem','fullchain.pem','privkey.pem']:
  q=(live/name).resolve();need(q.is_file() and q.is_relative_to(lab/'config/archive'),'certificado aponta fora do laboratório')
 cert=ssl._ssl._test_decode_cert(str(live/'cert.pem'))
 need(cert.get('subjectAltName')==(('DNS',DOMAIN),),'SAN inesperado')
 need(ssl.cert_time_to_seconds(cert['notAfter'])>time.time()+86400,'certificado vence antes de um dia')
 run(lab,'cadeia',['/usr/bin/openssl','verify','-purpose','sslserver','-verify_hostname',DOMAIN,'-CAfile',TRUST,'-untrusted',str(live/'chain.pem'),str(live/'cert.pem')])
 pubcert=subprocess.check_output(['/usr/bin/openssl','x509','-in',str(live/'cert.pem'),'-pubkey','-noout'],env=ENV)
 pubkey=subprocess.check_output(['/usr/bin/openssl','pkey','-in',str(live/'privkey.pem'),'-pubout'],env=ENV,stderr=subprocess.DEVNULL)
 need(pubcert==pubkey,'chave não corresponde ao certificado')
 return digest(ssl.PEM_cert_to_DER_cert((live/'cert.pem').read_text()))
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--executar',action='store_true');parser.add_argument('--hook',nargs=2,metavar=('LAB','ACAO'));a=parser.parse_args()
 if a.hook:
  lab=Path(a.hook[0]);need(lab.parent==Path('/var/tmp') and lab.name.startswith('santafe-acme-publico15-'),'laboratório inválido');need(a.hook[1] in ['autorizar','limpar'],'ação inválida');hook(lab,a.hook[1]);return
 need(a.executar,'Use --executar após conferir o roteiro; duas emissões públicas, sem instalação.')
 need(os.geteuid()==0,'Execute com sudo: apenas os desafios temporários precisam de acesso ao webroot.')
 os.umask(0o077)
 lock_path=Path('/var/tmp/santafe-acme-publico15.lock');fd=os.open(lock_path,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
 need(os.fstat(fd).st_uid==0,'lock não pertence a root');fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
 # A execução não aceita opções de domínio, hook ou caminho de produção.
 no_links(WEB);need(WEB.is_dir(),'webroot ausente')
 conf=regular(Path('/etc/nginx/sites-available/paodocafe.conf')).decode()
 need('location /.well-known/acme-challenge/' in conf and 'root /var/www/paodocafe.com.br;' in conf,'rota ACME capturada não corresponde')
 before=snapshot();account,account_path=choose_account()
 lab=Path(tempfile.mkdtemp(prefix='santafe-acme-publico15-',dir='/var/tmp'));lab.chmod(0o700)
 (lab/'tokens').mkdir();(lab/'vazio.ini').write_text('');shutil.copy2(Path(__file__).resolve(),lab/'roteiro.py')
 destination=lab/'config/accounts/acme-v02.api.letsencrypt.org/directory'/account;destination.mkdir(parents=True)
 for name in ['regr.json','meta.json','private_key.json']:(destination/name).write_bytes(regular(account_path/name))
 challenge=WEB/'.well-known/acme-challenge';created=[];report={'candidato':'dados.15','resultado':'EM_ANDAMENTO','instalacao':False,'servicos_reiniciados':False,'ordens_maximas':2,'certificados_servidos_inalterados':False}
 save(lab/'antes.json',before);save(lab/'contexto.json',{'dominio':DOMAIN,'desafios':str(challenge),'origem_http':'http://'+DOMAIN})
 try:
  for d in [WEB/'.well-known',challenge]:
   no_links(d)
   if not d.exists():d.mkdir(mode=0o755);d.chmod(0o755);created.append(d)
   need(d.is_dir(),'diretório de desafio inválido')
  run(lab,'emissao',command(lab,account));first=inspect_cert(lab)
  run(lab,'renovacao',command(lab,account,True));second=inspect_cert(lab)
  need(first!=second,'renovação não mudou o certificado')
  report.update(resultado='PASSOU_EMISSAO_RENOVACAO_PUBLICA',primeiro_sha256=first,renovado_sha256=second)
 except BaseException as e:
  report.update(resultado='FALHOU',falha=type(e).__name__+': '+str(e))
 finally:
  try:
   for rec in (lab/'tokens').glob('*.json'):clean_token(lab,rec)
   for d in reversed(created):
    try:d.rmdir()
    except OSError:need(any(d.iterdir()),'diretório vazio não pôde ser removido')
   records=[read(p) for p in (lab/'tokens').glob('*.json')]
   report['desafios_http_conferidos']=sum(x['http_conferido'] for x in records)
   report['desafios_limpos']=all(x['limpo'] for x in records)
   after=snapshot();save(lab/'depois.json',after);need(after==before,'estado da produção mudou; interromper e investigar')
   report['certificados_servidos_inalterados']=True;report['producao_inalterada']=True
  except BaseException as e:report.update(resultado='FALHOU',falha_final=type(e).__name__+': '+str(e))
  if report['resultado'].startswith('PASSOU') and not report.get('desafios_http_conferidos'):
   report['resultado']='EMISSAO_COM_AUTORIZACAO_REUTILIZADA';report['pendencia']='desafio público novo não observado'
  save(lab/'resultado.json',report)
 print('RESULTADO_ACME',report['resultado']);print('EVIDENCIA_PRIVADA',lab/'resultado.json')
 # Somente evidências públicas; chaves e conta nunca saem do diretório root.
 print(json.dumps({k:v for k,v in report.items() if k not in ['falha','falha_final']},ensure_ascii=False))
 need(report['resultado']=='PASSOU_EMISSAO_RENOVACAO_PUBLICA','ensaio incompleto; consulte o resultado privado')
if __name__=='__main__':
 try:main()
 except Exception as e:print('ERRO_ACME',e,file=sys.stderr);sys.exit(1)
