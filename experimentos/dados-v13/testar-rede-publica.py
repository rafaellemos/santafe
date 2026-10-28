#!/usr/bin/env python3
"""Consultas DNS/TLS e AUTH somente. Não envia DATA, mensagens, ou altera contas."""
from pathlib import Path
import argparse,hashlib,json,os,shlex,smtplib,socket,ssl,subprocess,time
ROOT=Path(__file__).resolve().parents[2];assert(ROOT/'.laboratorio-dados13').is_file()
p=argparse.ArgumentParser();p.add_argument('--credencial-capturada',type=Path);args=p.parse_args()
out=ROOT/'evidencias';out.mkdir(exist_ok=True)
r={'resultado':'EM_ANDAMENTO','grupos':[],'mensagens_enviadas':0,'producao_alterada':False}
def passed(name,**kw):r['grupos'].append({'grupo':name,**kw});print('PASSOU',name,flush=True)
units=['sfdev.service','paodocafe.service','carteiro.service','carteiro-paodocafe.service','correio-imap.service','correio-agencia.service','correio-recebedor.service']
def prod():
 data=subprocess.check_output(['systemctl','show','--property=Id,MainPID,ActiveEnterTimestampMonotonic',*units])
 assert b'MainPID=0\n' not in data
 return hashlib.sha256(data).hexdigest(),hashlib.sha256(Path('/usr/local/bin/santafé').read_bytes()).hexdigest()
before=prod()
try:
 for host in ['xn--santaf-gva.dev.br','xn--podocaf-xwa4d.com.br']:
  with socket.create_connection((host,443),timeout=15) as tcp,ssl.create_default_context().wrap_socket(tcp,server_hostname=host) as c:
   cert=c.getpeercert();assert ssl.cert_time_to_seconds(cert['notAfter'])>time.time()
   passed('HTTPS público com cadeia e nome verificados',dominio=host,tls=c.version(),certificado_sha256=hashlib.sha256(c.getpeercert(True)).hexdigest())
 dns=subprocess.run([str(ROOT/'src/santafé'),'-E','-P','experimentos/dados-v13/dns-publico.fé'],cwd=ROOT,env={k:os.environ[k] for k in ['PATH','LANG','LC_ALL'] if k in os.environ},capture_output=True,timeout=90)
 (out/'dns13.log').write_bytes(dns.stdout+dns.stderr)
 assert dns.returncode==0 and b'DNS_PUBLICO_CANDIDATO_OK' in dns.stdout,'DNS do candidato falhou; conferir dns13.log'
 passed('Núcleo candidato: SPF público positivo e falsificação local rejeitada')
 credentials={}
 if args.credencial_capturada:
  path=args.credencial_capturada.resolve();assert str(path).startswith('/var/tmp/santafe-migracao11-') and path.name=='mailjet.env'
  for row in path.read_text().splitlines():
   if not row.strip() or row.lstrip().startswith('#'):continue
   key,value=row.split('=',1);pieces=shlex.split(value)
   if key in ['MAILJET_SMTP_USUARIO','MAILJET_SMTP_SENHA','CORREIO_ENVIOS_USUARIO','CORREIO_ENVIOS_SENHA']:
    assert len(pieces)==1;credentials[key]=pieces[0]
 with smtplib.SMTP('in-v3.mailjet.com',587,timeout=25) as smtp:
  assert smtp.ehlo()[0]==250 and smtp.has_extn('starttls')
  smtp.starttls(context=ssl.create_default_context());assert smtp.ehlo()[0]==250
  assert smtp.has_extn('smtputf8') and smtp.has_extn('8bitmime')
  passed('Mailjet público: STARTTLS verificado, SMTPUTF8 e 8BITMIME',tls=smtp.sock.version())
  user=credentials.get('MAILJET_SMTP_USUARIO') or credentials.get('CORREIO_ENVIOS_USUARIO')
  password=credentials.get('MAILJET_SMTP_SENHA') or credentials.get('CORREIO_ENVIOS_SENHA')
  assert user and password,'credencial capturada ausente'
  code,_=smtp.login(user,password);assert code==235
  passed('Mailjet: autenticação somente, sem MAIL/RCPT/DATA')
  assert smtp.noop()[0]==250
 credentials.clear()
 r['resultado']='PASSOU'
finally:
 after=prod();r['nucleo_e_processos_inalterados']=before==after
 if before!=after:r['resultado']='FALHOU'
 (out/'rede-publica13.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
 assert before==after,'estado operacional mudou durante conferência'
