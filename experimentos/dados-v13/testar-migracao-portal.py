#!/usr/bin/env python3
"""Prova aplicação/reversão da correção sem escrever na réplica original."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('portal_capturado',type=Path);a=p.parse_args()
assert str(a.portal_capturado.resolve()).startswith('/var/tmp/santafe-migracao11-')
original=a.portal_capturado.read_bytes();original_hash=hashlib.sha256(original).hexdigest()
with tempfile.TemporaryDirectory(prefix='santafe-apps5-portal13-',dir='/tmp') as d:
 target=Path(d)/'sfdev.fé';target.write_bytes(original)
 cmd=[sys.executable,str(ROOT/'experimentos/dados-v13/migrar-portal.py'),str(target)]
 def run(extra=(),ok=True):
  r=subprocess.run(cmd+list(extra),capture_output=True,timeout=40)
  assert (r.returncode==0)==ok,'resultado de migração inesperado'
 run();after=hashlib.sha256(target.read_bytes()).hexdigest();assert after!=original_hash
 run(ok=False) # não aplica duas vezes
 patched=target.read_bytes();target.write_bytes(patched+b'\n-- alterado\n')
 run(['--reverter'],ok=False) # não descarta edição posterior
 target.write_bytes(patched);run(['--reverter']);assert target.read_bytes()==original
 assert a.portal_capturado.read_bytes()==original
 out={'resultado':'PASSOU','grupos':['aplicação e compilação na cópia','segunda aplicação recusada','reversão recusa edição posterior','reversão exata; réplica original inalterada'],'antes':original_hash,'depois':after,'producao_alterada':False}
 (ROOT/'evidencias/migracao-portal13.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 print('MIGRACAO_PORTAL13_OK',len(out['grupos']))
