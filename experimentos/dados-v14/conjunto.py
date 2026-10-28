#!/usr/bin/env python3
"""Integrações simultâneas na réplica aprovada; nenhuma rota de rede externa."""
from pathlib import Path
import argparse,email.policy,fcntl,hashlib,http.client,importlib.util,json,os,shutil,smtplib,subprocess,sys,threading,time,traceback
from email.message import EmailMessage
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE));from integracoes import Integracoes
spec=importlib.util.spec_from_file_location('base14',HERE/'carga-base.py');B=importlib.util.module_from_spec(spec);spec.loader.exec_module(B);M=B.M
class Conjunto(Integracoes,B.Carga):
 def env_unit(self,g,unit):
  env=super().env_unit(g,unit)
  if g.name=='candidata':
   env.update(CORREIO_AUTENTICACAO_ATIVA='verdadeiro',CORREIO_ANTIVIRUS_ATIVO='verdadeiro',CORREIO_TRIAGEM_ATIVA='verdadeiro',
    CORREIO_ANTIVIRUS_ENDERECO='127.0.0.1',CORREIO_ANTIVIRUS_PORTA='13310',CORREIO_ANTIVIRUS_TEMPO_LIMITE='3000',
    CORREIO_DKIM_EXIGIR='verdadeiro',CORREIO_DKIM_IDENTIDADES=','.join(d+'|ensaio14|/tmp/dkim14.pem' for d in M.DOMS),
    CORREIO_ENVIOS_ENDERECO='retransmissor.ensaio.test',CORREIO_ENVIOS_PORTA='12587',CORREIO_ENVIOS_SEGURANCA='inícioTLS',
    CORREIO_ENVIOS_VALIDAR_CERTIFICADO='verdadeiro',CORREIO_ENVIOS_USUARIO='ensaio14',CORREIO_ENVIOS_SENHA='somente-ensaio14',
    SANTAFE_DIRETORIO_IMAGENS_COMUNIDADE='/tmp/imagens14')
  return env
 def archive_logs(self):
  save=self.lab/('registros-antes14-'+str(time.time_ns()));save.mkdir()
  for p in self.lab.iterdir():
   if p.is_file() and p.suffix in ('.log','.jsonl','.pulso') and not p.name.startswith('dados14-'):p.rename(save/p.name)
  for p in list((self.lab/'candidata/var/log').rglob('*')):
   if p.is_file() and not p.is_symlink():
    dest=save/'var-log'/p.relative_to(self.lab/'candidata/var/log');dest.parent.mkdir(parents=True,exist_ok=True);p.rename(dest)
 def prepare_portal(self):
  p=self.lab/'candidata/opt/sfdev.fé';h=hashlib.sha256(p.read_bytes()).hexdigest()
  before='d0e14ec43993e5c01784dba2a0646a0ffb19d7f72ab20a8a049618316ac339d5';after='b286a5bdde86ec7f5c0a70d99ba994f65c86dfa1227df889f8b5f649d7bc3d5e'
  assert h in (before,after),'portal mudou; migração exige revisão'
  if h==before:
   spec=importlib.util.spec_from_file_location('patch13',ROOT/'experimentos/dados-v13/aplicar-portal.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.corrigir(p)
  assert hashlib.sha256(p.read_bytes()).hexdigest()==after
  self.run([self.stage/'src/santafec','-p',p])
  (self.lab/'candidata/tmp/imagens14').mkdir(exist_ok=True)
  self.passed('portal corrigido instalado e compilado somente na réplica')
 def protections(self):
  db=M.DBS[0];owner=self.owners[db]
  def count():return int(self.sql('SELECT COUNT(*) FROM correio_cartas;',db))
  def mail(sender='origem@ensaio.invalid',attachment=None,phishing=False):
   m=EmailMessage(policy=email.policy.SMTPUTF8);m['From']=sender;m['To']=self.user+'@'+M.DOMS[0];m['Subject']='Conjunto14 proteção'
   m.set_content('URGENTE confirme sua senha agora.' if phishing else 'Somente homologação.')
   if attachment is not None:m.add_attachment(attachment,maintype='application',subtype='octet-stream',filename='teste.txt')
   if phishing:m.add_alternative('<form action="http://203.0.113.20"><input type="password"></form><a href="http://203.0.113.20">https://banco.example</a>',subtype='html')
   with smtplib.SMTP('127.0.0.1',11025,timeout=20) as c:c.ehlo();return c.sendmail(sender,[self.user+'@'+M.DOMS[0]],m.as_bytes(),mail_options=['SMTPUTF8','BODY=8BITMIME'])
  def refuse(code,**kw):
   n=count()
   try:mail(**kw)
   except smtplib.SMTPDataError as e:assert (400<=e.smtp_code<500) if code=='temporaria' else e.smtp_code==code,(e.smtp_code,code)
   else:raise AssertionError('mensagem recusável foi aceita')
   assert count()==n
  mail();refuse(550,sender='falsa@recusado.test')
  eicar=b'X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*';refuse(554,attachment=eicar)
  mail(phishing=True);assert self.sql('SELECT pasta FROM correio_cartas ORDER BY id DESC LIMIT 1;',db).strip()=='indesejadas'
  self.stop([self.clam]);refuse('temporaria');self.clam_start()
  self.passed('recepção conjunta: SPF/DMARC, antivírus, fisgada e indisponibilidade recusam ou classificam sem perda')
 def upload(self):
  token=self.tokens[(M.DBS[0],self.owners[M.DBS[0]])]
  image=self.sf('candidata','mostre(colar.base64((importe "imagem").codifique("png",4,4,função(x,y) retorne 80*x,80*y,0,255 fim)))')
  import base64
  image=base64.b64decode(image);folder=self.lab/'candidata/tmp/imagens14'
  def form(data,csrf='replica11-csrf'):
   boundary='Conjunto14';body=b''
   for key,value in {'csrf':csrf,'categoria':'codigo','titulo':'Conjunto14 <teste>','conteudo':'Homologação com proteções ativas.','codigo':'local x=[nulo,1]','linguagem':'santafé','imagem_alt':'Ensaio'}.items():body+=('--'+boundary+'\r\nContent-Disposition: form-data; name="'+key+'"\r\n\r\n'+value+'\r\n').encode()
   body+=('--'+boundary+'\r\nContent-Disposition: form-data; name="imagem"; filename="../../ensaio.png"\r\nContent-Type: image/png\r\n\r\n').encode()+data+('\r\n--'+boundary+'--\r\n').encode()
   c=http.client.HTTPConnection('127.0.0.1',17000,timeout=15);c.request('POST','/comunidade/publicar',body,{'Cookie':'sf_sessao='+token,'Content-Type':'multipart/form-data; boundary='+boundary});r=c.getresponse();r.read();c.close();return r.status
  previous=set(folder.iterdir());assert form(image[:25])==400 and form(image,'errado')==403
  assert set(folder.iterdir())==previous;assert form(image)==303
  self.upload_files={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir()}
  assert len(self.upload_files)==len(previous)+1
  self.passed('upload na réplica real: truncamento/CSRF recusados; imagem válida persistida com proteções ativas')
 def load(self):
  errors=[];finished=threading.Event()
  def rotate():
   if finished.wait(120):return
   try:self.renew()
   except BaseException as e:errors.append(type(e).__name__+': '+str(e));(self.lab/'INTERROMPER-DADOS14').touch()
  thread=threading.Thread(target=rotate);thread.start()
  try:super().load()
  finally:finished.set();thread.join()
  assert not errors,'renovação durante carga falhou'
 def execute(self):
  self.reuse();self.archive_logs();self.prepare_portal();self.setup_integrations()
  before=self.tables();procs=self.services('candidata');infra=self.infrastructure('candidata');procs+=infra;self.nginx=infra[0]
  assert self.tables()==before,'inicialização alterou os bancos'
  self.read_all('candidata');self.protections();self.upload()
  self.protocols('candidata','dados14-antes')
  for db in M.DBS:
   n=int(self.sql("SELECT COUNT(*) FROM correio_cartas WHERE assunto LIKE '%dados14-antes%' AND direcao='entrada' AND resultado_spf='passa' AND resultado_dkim='passa' AND resultado_dmarc='passa';",db))
   assert n>=2,'assinaturas das duas saídas não foram verificadas'
  self.passed('filas isoladas: SMTP AUTH/TLS, assinatura DKIM, autenticação no destino e leitura IMAP nos dois domínios')
  self.load()
  # Consumidores postais novos recebem o certificado renovado; somente processos da réplica.
  self.stop(procs+[self.relay]);procs=self.services('candidata');infra=self.infrastructure('candidata');procs+=infra;self.nginx=infra[0]
  self.relay=self.start('retransmissor-renovado',self.command(self.g,code='executeArquivo("/tmp/retransmissor14.fé")'),self.env_unit(self.g,'carteiro.service'));self.wait(self.relay,12587)
  self.protocols('candidata','dados14-depois');self.read_all('candidata');self.objects()
  saved=self.tables();files={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in self.upload_files}
  assert files==self.upload_files
  self.stop(procs+[self.relay,self.clam,self.ca])
  stable=self.services('estavel');stable+=self.infrastructure('estavel')
  assert self.tables()==saved,'reversão alterou dados'
  self.read_all('estavel');self.objects()
  assert {p:hashlib.sha256(p.read_bytes()).hexdigest() for p in self.upload_files}==files
  self.stop(stable);self.passed('reversão conjunta preserva mensagens, anexos e imagem nova após renovação/carga')
  self.report['resultado']='PASSOU'
def main():
 p=argparse.ArgumentParser();p.add_argument('--lab',type=Path,required=True);p.add_argument('--replica',type=Path,required=True);p.add_argument('--candidato',type=Path,required=True);p.add_argument('--acme',type=Path,required=True);p.add_argument('--segundos',type=int,default=3600);p.add_argument('--interior',action='store_true');a=p.parse_args()
 assert 3600<=a.segundos<=7200 and (a.candidato/'.laboratorio-dados14').is_file()
 if not a.interior:
  lock=(a.lab/'execucao14.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  # Não reutilizar dados enquanto outro ensaio os mantém abertos.
  for proc in Path('/proc').glob('[0-9]*'):
   if int(proc.name)==os.getpid():continue
   try:command=(proc/'cmdline').read_bytes()
   except (PermissionError,FileNotFoundError,ProcessLookupError):continue
   if (str(a.lab/'dados').encode() in command or str(a.lab/'candidata').encode() in command) and any(x in command for x in (b'mariadbd',b'chroot')):raise RuntimeError('réplica ainda em uso')
  env=dict(M.BASE_ENV,SANTAFE_NET_ORIGEM=os.readlink('/proc/self/ns/net'));os.nice(15)
  raise SystemExit(subprocess.call(['unshare','--user','--map-root-user','--mount','--net','--pid','--fork',sys.executable,str(Path(__file__).resolve()),*sys.argv[1:],'--interior'],env=env))
 assert os.getpid()==1 and os.readlink('/proc/self/ns/net')!=os.environ['SANTAFE_NET_ORIGEM']
 assert {x['ifname'] for x in json.loads(subprocess.check_output(['ip','-j','link']))}=={'lo'}
 subprocess.run(['ip','link','set','lo','up'],check=True)
 # GNetworkAddress aplica AI_ADDRCONFIG: lo não basta para resolver nomes IPv4.
 # Interface dummy no namespace, sem par, gateway ou qualquer rota externa.
 subprocess.run(['ip','link','add','ensaio0','type','dummy'],check=True)
 subprocess.run(['ip','addr','add','192.0.2.1/32','dev','ensaio0'],check=True)
 subprocess.run(['ip','link','set','ensaio0','up'],check=True)
 assert {x['ifname'] for x in json.loads(subprocess.check_output(['ip','-j','link']))}=={'lo','ensaio0'}
 assert not json.loads(subprocess.check_output(['ip','-j','route','show','default']))
 assert not json.loads(subprocess.check_output(['ip','-j','-6','route','show','default']))
 os.umask(0o077)
 assert not(a.lab/'INTERROMPER-DADOS14').exists(),'interrupção anterior requer revisão'
 x=Conjunto(a)
 try:x.execute()
 except BaseException as e:
  x.report.update(resultado='FALHOU',falha=type(e).__name__+': '+str(e));(x.lab/'rastro-dados14-privado.txt').write_text(traceback.format_exc());print('FALHOU',type(e).__name__,flush=True)
 finally:
  x.stop(x.procs)
  for h in x.handles:h.close()
  M.write(x.lab/'resultado-dados14.json',x.report)
 if x.report['resultado']!='PASSOU':raise SystemExit(1)
if __name__=='__main__':main()
