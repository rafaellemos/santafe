#!/usr/bin/env python3
"""Restaura os dois DBs copiados num MariaDB privado sem rede externa.
Primeiro gate da migração; NÃO é homologação dos aplicativos migrados.
"""
from pathlib import Path
import argparse, hashlib, importlib.util, json, os, re, shutil, subprocess, sys, tempfile, time
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('verifica',HERE/'verificar-replica.py');V=importlib.util.module_from_spec(spec);spec.loader.exec_module(V)

def ident(s):return '`'+s.replace('`','``')+'`'
def main():
 p=argparse.ArgumentParser();p.add_argument('replica',type=Path);p.add_argument('--interior',action='store_true');a=p.parse_args()
 root=a.replica.absolute()
 if sys.platform!='linux':raise SystemExit('restauração completa exige namespace Linux')
 if not a.interior:
  V.conferir(root)
  env={k:os.environ[k] for k in ('PATH','LANG','LC_ALL') if k in os.environ}
  env['SANTAFE_NET_ORIGEM']=os.readlink('/proc/self/ns/net')
  cmd=['unshare','--user','--map-root-user','--net',sys.executable,str(Path(__file__).resolve()),str(root),'--interior']
  raise SystemExit(subprocess.call(cmd,env=env))
 if not os.environ.get('SANTAFE_NET_ORIGEM') or os.readlink('/proc/self/ns/net')==os.environ['SANTAFE_NET_ORIGEM']:
  raise SystemExit('rede não isolada')
 # /sys é uma montagem do host e pode conservar a visão antiga; netlink
 # consulta as interfaces do namespace de rede atual.
 links=json.loads(subprocess.check_output(['ip','-j','link'],text=True))
 if {x['ifname'] for x in links}!={'lo'}:raise SystemExit('interface externa no laboratório')
 subprocess.run(['ip','link','set','lo','up'],check=True)
 if subprocess.check_output(['ip','route','show','default']).strip():raise SystemExit('rota externa detectada')
 m=V.conferir(root)
 os.umask(0o077);lab=Path(tempfile.mkdtemp(prefix='santafe-restauro10-',dir='/var/tmp'))
 (lab/'.restauro-privado').write_text('Dados operacionais copiados. Não enviar a terceiros.\n')
 (lab/'exportacao').mkdir();(lab/'sem-plugins').mkdir()
 env={k:os.environ[k] for k in ('PATH','LANG','LC_ALL') if k in os.environ}
 server=None;handle=(lab/'mariadb.log').open('w')
 try:
  subprocess.run(['mariadb-install-db','--no-defaults','--datadir='+str(lab/'dados'),'--auth-root-authentication-method=normal','--skip-test-db'],stdout=handle,stderr=handle,check=True,timeout=90,env=env)
  sock=lab/'b.sock'
  cmd=[shutil.which('mariadbd') or '/usr/sbin/mariadbd','--no-defaults','--user=root','--datadir='+str(lab/'dados'),'--socket='+str(sock),'--pid-file='+str(lab/'pid'),'--skip-networking','--skip-log-bin','--event-scheduler=DISABLED','--local-infile=0','--skip-symbolic-links','--secure-file-priv='+str(lab/'exportacao'),'--plugin-dir='+str(lab/'sem-plugins'),'--innodb-buffer-pool-size=128M']
  server=subprocess.Popen(cmd,stdout=handle,stderr=handle,env=env)
  client=['mariadb','--no-defaults','--protocol=socket','--socket='+str(sock),'-uroot','--batch','--raw','--skip-column-names','--binary-mode','--local-infile=0']
  def sql(q):
   r=subprocess.run(client,input=q,text=True,capture_output=True,env=env,timeout=120)
   if r.returncode:
    (lab/'consulta-falha.txt').write_text(r.stderr);raise RuntimeError('consulta no banco privado falhou')
   return r.stdout
  for _ in range(200):
   if server.poll() is not None:raise RuntimeError('MariaDB privado não iniciou')
   if sock.exists():
    try:sql('SELECT 1;');break
    except RuntimeError:pass
   time.sleep(.05)
  else:raise RuntimeError('timeout no MariaDB privado')
  with (root/'bancos.sql').open('rb') as dump,(lab/'restauracao.log').open('wb') as log:
   p=subprocess.run(client,stdin=dump,stdout=log,stderr=log,env=env,timeout=900)
  if p.returncode:raise RuntimeError('dump não restaurado')
  stats={};integrity={}
  for db,deposit in (('santafe_comunidade','var/lib/santafé/correio'),('paodocafe','var/lib/paodocafe/correio')):
   tables=[x.split('\t')[0] for x in sql('SHOW FULL TABLES FROM '+ident(db)+' WHERE Table_type="BASE TABLE";').splitlines()]
   stats[db]={}
   for table in tables:
    name=ident(db)+'.'+ident(table)
    count=int(sql('SELECT COUNT(*) FROM '+name+';').strip())
    checksum=sql('CHECKSUM TABLE '+name+' EXTENDED;').strip().split('\t')[-1]
    stats[db][table]={'linhas':count,'checksum':checksum}
   objects=set()
   for table,col in (('correio_cartas','mime_objeto'),('correio_anexos','dados_objeto'),('correio_fila','conteudo_objeto')):
    if table not in tables:raise RuntimeError('tabela postal ausente na cópia')
    objects.update(x for x in sql('SELECT DISTINCT '+ident(col)+' FROM '+ident(db)+'.'+ident(table)+' WHERE '+ident(col)+' IS NOT NULL;').splitlines() if x)
   for digest in objects:
    if not re.fullmatch('[0-9a-f]{64}',digest):raise RuntimeError('referência de objeto inválida')
    name=deposit+'/objetos/'+digest[:2]+'/'+digest[2:4]+'/'+digest
    if name not in m['arquivos'] or V.resumo(root/'arquivos'/name)!=digest:raise RuntimeError('depósito inconsistente com o dump')
   integrity[db]={'objetos_referenciados':len(objects),'tabelas':len(tables)}
  (lab/'baseline.json').write_text(json.dumps({'tabelas':stats,'integridade':integrity,'sql_sha256':m['sql_sha256'],'rede_isolada':True},ensure_ascii=False,indent=2)+'\n')
  (lab/'GATE_RESTAURACAO_OK').write_text('Somente restauração/integridade. Migração e rollback dos aplicativos ainda pendentes.\n')
  print('RESTAURACAO_INTEGRA',lab,json.dumps(integrity,ensure_ascii=False))
 finally:
  if server and server.poll() is None:
   server.terminate()
   try:server.wait(timeout=30)
   except subprocess.TimeoutExpired:server.kill();server.wait()
  handle.close()
if __name__=='__main__':main()
