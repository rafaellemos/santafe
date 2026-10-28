#!/usr/bin/env python3
"""Leitura pública e de processos; não administra serviços."""
from pathlib import Path
import argparse,hashlib,json,subprocess,time,urllib.request
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidencias';E.mkdir(exist_ok=True)
p=argparse.ArgumentParser();p.add_argument('fase',choices=['antes','depois']);a=p.parse_args()
units=['sfdev.service','paodocafe.service','carteiro.service','carteiro-paodocafe.service','correio-imap.service','correio-agencia.service','correio-recebedor.service']
def snapshot():
 b=subprocess.check_output(['systemctl','show','--property=Id,MainPID,ActiveEnterTimestampMonotonic',*units])
 assert b.count(b'MainPID=')==7 and b'MainPID=0\n' not in b
 return {'processos_sha256':hashlib.sha256(b).hexdigest(),'nucleo_sha256':hashlib.sha256(Path('/usr/local/bin/santafé').read_bytes()).hexdigest()}
s=snapshot();r=subprocess.run(['/usr/local/bin/santafé','-v'],capture_output=True,timeout=10)
assert r.returncode==0 and b'2.1.0' in r.stdout+r.stderr
before=E/'producao15-inicio.json'
if a.fase=='antes':
 with before.open('x') as f:json.dump({'inicio':time.time(),'estado':s},f)
 print('PRODUCAO_BASELINE_OK');raise SystemExit()
v=json.loads(before.read_text());assert v['estado']==s
n=0
for host in ['xn--santaf-gva.dev.br','xn--podocaf-xwa4d.com.br']:
 for route in ['/','/carteiro/']:
  with urllib.request.urlopen('https://'+host+route,timeout=20) as f:assert f.status==200;n+=1
assert snapshot()==s
(E/'producao15.json').write_text(json.dumps({'resultado':'PASSOU','versao':'2.1.0','servicos_ativos':7,'http_200':n,'nucleo_e_processos_inalterados':True,'inicio':v['inicio'],'fim':time.time()},indent=2)+'\n')
print('PRODUCAO15_CONFERIDA',n)
