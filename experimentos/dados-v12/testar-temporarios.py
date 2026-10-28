#!/usr/bin/env python3
"""Prova negativa/positiva da limpeza #sql, somente em diretórios sintéticos."""
from pathlib import Path
import json,os,shutil,socket,subprocess,tempfile,time
R=Path(__file__).resolve().parents[2]
assert(R/'.laboratorio-dados12').is_file()
assert shutil.disk_usage('/tmp').free>2300*1024**2
os.umask(0o077);lab=Path(tempfile.mkdtemp(prefix='santafe-tmp12-',dir='/tmp'));rows=[];server=None
shared=lab/'a';private=lab/'b';shared.mkdir();private.mkdir()
env={k:os.environ[k] for k in ('PATH','LANG','LC_ALL') if k in os.environ}
env['TMPDIR']=str(private)
with (lab/'bootstrap.log').open('wb') as log:
 subprocess.run(['mariadb-install-db','--no-defaults','--tmpdir='+str(private),'--datadir='+str(lab/'dados'),'--auth-root-authentication-method=normal','--skip-test-db'],env=env,stdout=log,stderr=log,check=True,timeout=90)
try:
 for label,tmp,preserve in [('compartilhado',shared,False),('isolado',private,True)]:
  canary=shared/'#sql-prova-dados12.MAI';canary.write_bytes(b'arquivo sentinela sintetico; nao e tabela de producao')
  with (lab/(label+'.log')).open('wb') as log:
   server=subprocess.Popen([shutil.which('mariadbd') or '/usr/sbin/mariadbd','--no-defaults','--datadir='+str(lab/'dados'),'--tmpdir='+str(tmp),'--socket='+str(lab/'b.sock'),'--pid-file='+str(lab/'pid'),'--skip-networking','--skip-log-bin','--innodb-buffer-pool-size=16M'],env=env,stdout=log,stderr=log)
   sql=['mariadb','--no-defaults','--protocol=socket','--socket='+str(lab/'b.sock'),'-uroot','-N']
   for _ in range(300):
    assert server.poll() is None
    q=subprocess.run(sql,input='SELECT @@tmpdir;',text=True,capture_output=True,timeout=3)
    if q.returncode==0:break
    time.sleep(.05)
   else:raise RuntimeError('instância sintética não iniciou')
   assert Path(q.stdout.strip()).resolve()==tmp.resolve()
   assert canary.exists()==preserve,(label,canary.exists())
   rows.append({'caso':label,'sentinela_preservada':preserve,'tmpdir_conferido':True});server.terminate();server.wait(timeout=30);server=None
 report={'resultado':'PASSOU','casos':rows,'limites':'sentinela prova mecanismo de limpeza; HTTP 503 capturado separadamente no teste dos aplicativos','laboratorio':str(lab)}
 (R/'evidencias/temporarios12.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print('TEMPORARIOS12_OK: compartilhado remove; isolado preserva; sem tocar /tmp/#sql do host')
finally:
 if server and server.poll() is None:server.terminate();server.wait(timeout=30)
 # Remoção apenas da base sintética recém-criada; preservar logs e evidência.
 shutil.rmtree(lab/'dados')
