#!/usr/bin/env python3
"""Ensaia verificações e restauração com cópia SINTÉTICA; não é migração real."""
from pathlib import Path
import hashlib, importlib.util, json, os, subprocess, sys, tempfile
H=Path(__file__).resolve().parent;R=H.parents[1]
if sys.platform!='linux':raise SystemExit('teste de namespace exige Debian')
spec=importlib.util.spec_from_file_location('v',H/'verificar-replica.py');V=importlib.util.module_from_spec(spec);spec.loader.exec_module(V)
os.umask(0o077);root=Path(tempfile.mkdtemp(prefix='santafe-replica-dados10-sintetica-',dir='/var/tmp'))
(root/'.replica-privada').write_text('sintético\n');(root/'PRONTO_PARA_ADAPTAR').write_text('sintético\n')
units={n:'' for n in ('sfdev.service','correio-imap.service','correio-recebedor.service','carteiro.service','carteiro-paodocafe.service','paodocafe.service')}
(root/'unidades.json').write_text(json.dumps(units))
files={}
def add(name,data):
 p=root/'arquivos'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
 files[name]={'sha256':hashlib.sha256(data).hexdigest(),'tamanho':len(data),'modo':0o600,'uid':os.geteuid(),'gid':os.getegid()}
for n in ('usr/local/bin/santafé','usr/local/bin/santafec','opt/sfdev.fé','opt/carteiro/carteiro.fé','opt/correio/imap.fé','opt/paodocafe/paodocafe.fé','usr/local/share/santafé/1.0/ensaio.fé','etc/paodocafe/banco.env','etc/santafe/correio.env'):add(n,b'fixture sem segredos')
body=b'From: teste@ensaio.test\r\nSubject: ensaio\r\n\r\nconteudo sintetico\r\n';digest=hashlib.sha256(body).hexdigest();sql=[]
for db,deposit in (('santafe_comunidade','var/lib/santafé/correio'),('paodocafe','var/lib/paodocafe/correio')):
 add(deposit+'/objetos/'+digest[:2]+'/'+digest[2:4]+'/'+digest,body)
 sql.append('CREATE DATABASE '+db+'; USE '+db+';')
 for tab,col in (('correio_cartas','mime_objeto'),('correio_anexos','dados_objeto'),('correio_fila','conteudo_objeto')):
  sql.append('CREATE TABLE '+tab+' (id BIGINT PRIMARY KEY,'+col+' CHAR(64), metadado TEXT NULL) ENGINE=InnoDB; INSERT INTO '+tab+" VALUES(137,'"+digest+"',NULL);")
(root/'bancos.sql').write_text('\n'.join(sql));m={'formato':1,'bancos':['santafe_comunidade','paodocafe'],'arquivos':files,'sql_sha256':V.resumo(root/'bancos.sql')}
def manifest(): (root/'manifesto.json').write_text(json.dumps(m))
manifest();results=[]
def passed(name):results.append(name);print('PASSOU',name,flush=True)
def refused(name,action,undo):
 action()
 try:
  try:V.conferir(root)
  except (ValueError,OSError):passed(name)
  else:raise AssertionError('aceitou '+name)
 finally:undo()
try:
 V.conferir(root);passed('cópia privada sintética íntegra')
 p=root/'arquivos/opt/sfdev.fé';old=p.read_bytes()
 refused('conteúdo adulterado',lambda:p.write_bytes(b'alterado'),lambda:p.write_bytes(old))
 refused('dump adulterado',lambda:(root/'bancos.sql').write_text('SELECT 7;'),lambda:(root/'bancos.sql').write_text('\n'.join(sql)))
 refused('arquivo exposto',lambda:p.chmod(0o644),lambda:p.chmod(0o600))
 def symlink():p.unlink();p.symlink_to('/etc/passwd')
 def restore():p.unlink();p.write_bytes(old)
 refused('symlink externo',symlink,restore)
 def traversal():m['arquivos']['../escape']={'sha256':'0'*64,'tamanho':1};manifest()
 def untraversal():del m['arquivos']['../escape'];manifest()
 refused('path traversal',traversal,untraversal)
 def missing():m['bancos']=['paodocafe'];manifest()
 def unmissing():m['bancos']=['santafe_comunidade','paodocafe'];manifest()
 refused('banco ausente',missing,unmissing)
 env={k:v for k,v in os.environ.items() if k!='SANTAFE_NET_ORIGEM'}
 r=subprocess.run([sys.executable,H/'restaurar-replica.py',root,'--interior'],capture_output=True,text=True,env=env)
 assert r.returncode and 'rede não isolada' in r.stderr;passed('recusa execução sem namespace')
 r=subprocess.run([sys.executable,H/'restaurar-replica.py',root],capture_output=True,text=True,timeout=180)
 assert r.returncode==0,(r.stdout,r.stderr);assert 'RESTAURACAO_INTEGRA' in r.stdout;passed('restauração de ambos os bancos e integridade dos objetos, rede isolada')
 # Keep manifest internally consistent but remove one referenced object: the
 # DB/filesystem gate must still detect it after a successful SQL restoration.
 name='var/lib/paodocafe/correio/objetos/'+digest[:2]+'/'+digest[2:4]+'/'+digest
 del m['arquivos'][name];(root/'arquivos'/name).unlink();manifest()
 r=subprocess.run([sys.executable,H/'restaurar-replica.py',root],capture_output=True,text=True,timeout=180)
 assert r.returncode and 'depósito inconsistente' in r.stderr,(r.stdout,r.stderr);passed('recusa depósito divergente do snapshot SQL')
finally:
 (R/'evidencias').mkdir(exist_ok=True)
 (R/'evidencias/replica10-sintetica.json').write_text(json.dumps({'passaram':results,'esperados':10,'sintetico':True,'replica_real_validada':False,'fixture':str(root)},ensure_ascii=False,indent=2)+'\n')
