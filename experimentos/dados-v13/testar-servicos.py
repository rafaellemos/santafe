#!/usr/bin/env python3
"""ClamAV real, triagem e upload do portal: somente banco/diretórios sintéticos."""
from pathlib import Path
import importlib.util
import argparse,base64,email.policy,hashlib,http.client,json,os,re,shutil,smtplib,socket,sys,time,zipfile,subprocess
from email.message import EmailMessage
from http.client import HTTPConnection
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'experimentos/dados-v5'))
from laboratorio import Lab,port
assert (ROOT/'.laboratorio-dados13').is_file()
parser=argparse.ArgumentParser();parser.add_argument('--portal',type=Path,required=True);parser.add_argument('--interior',action='store_true');args=parser.parse_args()
if not args.interior:
 env={k:os.environ[k] for k in ('PATH','LANG','LC_ALL') if k in os.environ};env['ENSAIO_NET_ORIGEM']=os.readlink('/proc/self/ns/net')
 raise SystemExit(subprocess.call(['unshare','--user','--map-root-user','--mount','--net','--pid','--fork','--mount-proc',sys.executable,str(Path(__file__).resolve()),*sys.argv[1:],'--interior'],env=env))
assert os.getpid()==1 and os.readlink('/proc/self/ns/net')!=os.environ['ENSAIO_NET_ORIGEM']
assert {x['ifname'] for x in json.loads(subprocess.check_output(['ip','-j','link']))}=={'lo'}
subprocess.run(['ip','link','set','lo','up'],check=True);os.umask(0o077)
class IsolatedLab(Lab):
 def start(self,name,args,extra=None):
  if name=='mariadb':args=[*args,'--user=root']
  return super().start(name,args,extra)
assert args.portal.is_file() and str(args.portal.resolve()).startswith('/var/tmp/santafe-migracao11-')
results=[];report={'resultado':'EM_ANDAMENTO','grupos':results,'dados':'sinteticos','producao_alterada':False}
def passed(s):results.append(s);print('PASSOU',s,flush=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
with IsolatedLab() as lab:
 report['laboratorio']=str(lab.path)
 assert shutil.disk_usage(lab.path).free>2300*1024**2,'reserva de disco insuficiente'
 try:
  # Base de assinaturas copiada, somente leitura; não se conecta ao clamd operacional.
  db=lab.path/'assinaturas';db.mkdir(mode=0o700)
  daily=Path('/var/lib/clamav/daily.cld');assert daily.is_file() and os.access(daily,os.R_OK)
  shutil.copyfile(daily,db/'daily.cld');report['assinaturas_sha256']=sha(db/'daily.cld')
  eicar=b'X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*'
  (db/'homologacao.hdb').write_text(hashlib.md5(eicar).hexdigest()+':'+str(len(eicar))+':Santafe.Ensaio.Eicar\n')
  avport=port();cfg=lab.path/'clamd.conf'
  cfg.write_text('Foreground yes\nTCPSocket '+str(avport)+'\nTCPAddr 127.0.0.1\nDatabaseDirectory '+str(db)+'\nTemporaryDirectory '+str(lab.path)+'\nLogFile '+str(lab.path/'clamd-motor.log')+'\nLogFileMaxSize 2M\nPidFile '+str(lab.path/'clamd.pid')+'\nMaxThreads 2\nMaxQueue 4\nStreamMaxLength 8M\nMaxScanSize 16M\nMaxFileSize 8M\nSelfCheck 0\n')
  av=lab.start('clamd',['/usr/sbin/clamd','--config-file='+str(cfg)])
  for _ in range(600):
   assert av.poll() is None,'motor antivírus encerrou'
   try:
    with socket.create_connection(('127.0.0.1',avport),timeout=.3) as c:
     c.sendall(b'zPING\0');assert c.recv(32)==b'PONG\0'
    break
   except (OSError,AssertionError):time.sleep(.1)
  else:raise AssertionError('motor não ficou pronto')
  cases=[('limpo',b'Conteudo de homologacao.',True),('eicar',eicar,False)]
  zipped=lab.path/'eicar.zip'
  with zipfile.ZipFile(zipped,'w',zipfile.ZIP_DEFLATED) as z:z.writestr('teste.txt',eicar)
  cases.append(('zip',zipped.read_bytes(),False))
  for name,content,clean in cases:
   f=lab.path/(name+'.bin');f.write_bytes(content)
   lab.env.update(ENSAIO_CLAMD_PORTA=str(avport),ENSAIO_CLAMD_ARQUIVO=str(f),ENSAIO_CLAMD_LIMPA='1' if clean else '0')
   run=lab.run([str(ROOT/'src/santafé'),'-E','-P',str(ROOT/'experimentos/dados-v13/antivirus-real.fé')])
   assert 'CLAMD_REAL_OK' in run.stdout
  passed('ClamAV real: INSTREAM limpo, EICAR e arquivo ZIP')
  lab.database();token='homologacao13-sessao';csrf='homologacao13-csrf'
  digest=lab.sf('mostre((importe "segredo").resumaBilhete("'+token+'"))')
  lab.sql("INSERT INTO usuarios(nome,usuario,email,senha_hash) VALUES ('Homologação','homologa','homologa@ensaio.test','nao-utilizavel'); INSERT INTO correio_caixas(usuario_id,parte_local,dominio_ascii,endereco_exibido,nome_exibido) VALUES(1,'homologa','ensaio.test','homologa@ensaio.test','Homologação'); INSERT INTO sessoes(usuario_id,token_hash,csrf_token,expira_em) VALUES(1,'"+digest+"','"+csrf+"',DATE_ADD(NOW(),INTERVAL 1 HOUR));")
  smtpport=port()
  lab.env.update(CORREIO_RAIZ=str(ROOT/'aplicativos/correio'),CORREIO_DOMINIO='ensaio.test',CORREIO_DOMINIOS_LOCAIS='ensaio.test',CORREIO_DEPOSITO=str(lab.path/'deposito'),CORREIO_PULSO_ARQUIVO=str(lab.path/'ensaio.pulso'),CORREIO_AUTENTICACAO_ATIVA='falso',CORREIO_ANTIVIRUS_ATIVO='verdadeiro',CORREIO_ANTIVIRUS_ENDERECO='127.0.0.1',CORREIO_ANTIVIRUS_PORTA=str(avport),CORREIO_ANTIVIRUS_TEMPO_LIMITE='3000',CORREIO_TRIAGEM_ATIVA='verdadeiro',CORREIO_DKIM_EXIGIR='falso',CORREIO_RECEBEDOR_ENDERECO='127.0.0.1',CORREIO_RECEBEDOR_PORTA=str(smtpport),CORREIO_RECEBEDOR_NOME='ensaio.test')
  receiver=lab.app('recebedor','aplicativos/correio/recebedor.fé');lab.wait(receiver,smtpport,'recebedor')
  for _ in range(150):
   if 'bancos postais, estruturas e segurança prontos' in (lab.path/'recebedor.log').read_text():break
   assert receiver.poll() is None;time.sleep(.1)
  else:raise AssertionError('recebedor não ficou pronto')
  def mail(text,attachment=None,html=None):
   m=EmailMessage(policy=email.policy.SMTP);m['From']='Ensaio <origem@fora.test>';m['To']='homologa@ensaio.test';m['Subject']='Ensaio isolado'
   m.set_content(text)
   if html:m.add_alternative(html,subtype='html')
   if attachment is not None:m.add_attachment(attachment,maintype='application',subtype='octet-stream',filename='ensaio.txt')
   with smtplib.SMTP('127.0.0.1',smtpport,timeout=15) as c:return c.sendmail('origem@fora.test',['homologa@ensaio.test'],m.as_bytes())
  assert mail('Uma mensagem limpa da homologação.')=={}
  assert lab.sql('SELECT COUNT(*) FROM correio_cartas')=='1'
  assert lab.sql('SELECT pasta FROM correio_cartas')=='entrada'
  try:mail('Anexo sintético de teste.',eicar);raise AssertionError('EICAR aceito')
  except smtplib.SMTPDataError as exc:assert exc.smtp_code==554,exc.smtp_code
  assert lab.sql('SELECT COUNT(*) FROM correio_cartas')=='1'
  passed('SMTP real: limpo persistido; ameaça 554 sem persistência')
  assert mail('URGENTE confirme sua senha agora.',html='<form action="http://203.0.113.20"><input type="password"></form><a href="http://203.0.113.20">https://banco.example</a>')=={}
  assert lab.sql('SELECT pasta FROM correio_cartas ORDER BY id DESC LIMIT 1')=='indesejadas'
  passed('Triagem Santafé real: mensagem de fisgada em Indesejadas')
  av.terminate();av.wait(timeout=15)
  try:mail('Indisponibilidade do motor.');raise AssertionError('carta aceita sem motor')
  except smtplib.SMTPDataError as exc:assert 400<=exc.smtp_code<500,exc.smtp_code
  assert lab.sql('SELECT COUNT(*) FROM correio_cartas')=='2'
  passed('Indisponibilidade do antivírus: recusa temporária sem persistência')
  # Nenhuma leitura dos bancos privados: portal real com identidade e schema de ensaio.
  lab.sql("CREATE TABLE publicacoes(id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,usuario_id BIGINT UNSIGNED NOT NULL,categoria VARCHAR(32),titulo VARCHAR(160),conteudo TEXT,codigo MEDIUMTEXT,linguagem VARCHAR(40),imagem_arquivo VARCHAR(255),imagem_alt VARCHAR(180),estado VARCHAR(20) NOT NULL DEFAULT 'publicado',criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP);")
  images=lab.path/'imagens';images.mkdir();pp=port();portal=lab.path/'sfdev.fé';shutil.copy2(args.portal,portal)
  spec=importlib.util.spec_from_file_location('portalpatch',ROOT/'experimentos/dados-v13/aplicar-portal.py');patch=importlib.util.module_from_spec(spec);spec.loader.exec_module(patch)
  report['portal_correcao']=patch.corrigir(portal)
  report['portal_sha256']=sha(portal)
  lab.env.update(SANTAFE_DIRETORIO_IMAGENS_COMUNIDADE=str(images),SANTAFE_PORTA=str(pp))
  p=lab.app('portal',str(portal));lab.wait(p,pp,'portal')
  def http(path,data=None,headers=None,cookie=True):
   h={'Cookie':'sf_sessao='+token} if cookie else {};h.update(headers or {})
   c=HTTPConnection('127.0.0.1',pp,timeout=20);c.request('POST' if data is not None else 'GET',path,data,h)
   r=c.getresponse();b=r.read();v=(r.status,dict(r.getheaders()),b);c.close();return v
  for _ in range(150):
   r=http('/comunidade/nova')
   if r[0]==200:break
   time.sleep(.1)
  assert r[0]==200,'formulário indisponível'
  png=lab.path/'sintetico.png';lab.sf('(importe "imagem").salve('+json.dumps(str(png))+',"png",8,8,função(x,y) retorne x*30,y*30,120,255 fim)')
  def form(image=None,name='imagem.png',mime='image/png',csrfvalue=csrf,cookie=True):
   boundary='Santafe13Ensaio';body=b''
   fields={'csrf':csrfvalue,'categoria':'codigo','titulo':'Ensaio <script>','conteudo':'Somente homologação isolada; ação e nulo.','codigo':'local lista=[nulo,1]','linguagem':'santafé','imagem_alt':'Descrição <script>'}
   for k,v in fields.items():body+=('--'+boundary+'\r\nContent-Disposition: form-data; name="'+k+'"\r\n\r\n'+v+'\r\n').encode()
   if image is not None:body+=('--'+boundary+'\r\nContent-Disposition: form-data; name="imagem"; filename="'+name+'"\r\nContent-Type: '+mime+'\r\n\r\n').encode()+image+b'\r\n'
   body+=('--'+boundary+'--\r\n').encode()
   return http('/comunidade/publicar',body,{'Content-Type':'multipart/form-data; boundary='+boundary},cookie)
  assert form(png.read_bytes(),csrfvalue='errado')[0]==403
  assert form(png.read_bytes(),cookie=False)[0]==401
  assert lab.sql('SELECT COUNT(*) FROM publicacoes')=='0' and not list(images.iterdir())
  passed('Upload real: autenticação e CSRF recusam antes da escrita')
  for image,name,mime in [(b'<script>executar()</script>','imagem.png','image/png'),(png.read_bytes()[:25],'incompleta.png','image/png'),(b'x'*(2*1024**2+1),'grande.png','image/png'),(png.read_bytes()[:-12],'sem-fim.png','image/png'),(png.read_bytes()[:-5]+b'X'+png.read_bytes()[-4:],'crc.png','image/png'),((ROOT/'testes/recursos/mat-santafe.jpg').read_bytes()[:-2],'truncada.jpg','image/jpeg')]:
   status=form(image,name,mime)[0];assert status in (400,413),(name,status)
  assert lab.sql('SELECT COUNT(*) FROM publicacoes')=='0' and not list(images.iterdir())
  passed('Upload real: conteúdo falso, truncado e acima do limite recusados')
  for image,name,mime in [(png.read_bytes(),'../../fora.png','image/png'),((ROOT/'testes/recursos/mat-santafe.jpg').read_bytes(),'foto.jpg','image/jpeg'),(None,'','')]:
   status,headers,body=form(image,name,mime);assert status==303,('publicação',status)
   status,headers,body=http(headers['Location']);assert status==200
   assert b'Ensaio &lt;script&gt;' in body and b'<script>executar()' not in body
  assert lab.sql('SELECT COUNT(*) FROM publicacoes')=='3'
  saved=list(images.iterdir());assert len(saved)==2 and all(p.parent==images and re.fullmatch(r'[a-zA-Z0-9_.-]+',p.name) for p in saved)
  assert not (lab.path/'fora.png').exists()
  passed('Upload real: PNG/JPEG, nome seguro, publicação sem imagem e leitura escapada')
  before={p.name:sha(p) for p in saved};lab.sql('DROP TABLE publicacoes;')
  assert form(png.read_bytes())[0]==500
  assert {p.name:sha(p) for p in images.iterdir()}==before
  passed('Falha SQL do upload: imagem recém-gravada removida; anteriores preservadas')
  report['resultado']='PASSOU'
 finally:
  report['disco_livre_mib']=shutil.disk_usage(lab.path).free//1024**2
  (ROOT/'evidencias').mkdir(exist_ok=True)
  (ROOT/'evidencias/servicos13.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
