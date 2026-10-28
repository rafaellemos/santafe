#!/usr/bin/env python3
"""Somente leitura: versão, sete processos e quatro respostas HTTPS públicas."""
from pathlib import Path
import hashlib,json,subprocess,urllib.request
ROOT=Path(__file__).resolve().parents[2]
units=['sfdev.service','paodocafe.service','carteiro.service','carteiro-paodocafe.service','correio-imap.service','correio-agencia.service','correio-recebedor.service']
def snapshot():
 b=subprocess.check_output(['systemctl','show','--property=Id,MainPID,ActiveEnterTimestampMonotonic',*units])
 assert b.count(b'MainPID=')==7 and b'MainPID=0\n' not in b
 return hashlib.sha256(b).hexdigest(),hashlib.sha256(Path('/usr/local/bin/santafé').read_bytes()).hexdigest()
before=snapshot()
r=subprocess.run(['/usr/local/bin/santafé','-v'],capture_output=True,timeout=10)
assert r.returncode==0 and b'2.1.0' in r.stdout+r.stderr
n=0
for host in ['xn--santaf-gva.dev.br','xn--podocaf-xwa4d.com.br']:
 for path in ['/','/carteiro/']:
  with urllib.request.urlopen('https://'+host+path,timeout=20) as f:assert f.status==200;n+=1
assert snapshot()==before
(ROOT/'evidencias/producao13.json').write_text(json.dumps({'resultado':'PASSOU','versao':'2.1.0','servicos_ativos':7,'http_200':n,'nucleo_e_processos_inalterados_durante_conferencia':True},indent=2)+'\n')
print('PRODUCAO13_CONFERIDA',n)
