#!/usr/bin/env python3
"""Aplica/reverte a correção de upload somente numa cópia privada do portal."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, os, shutil, subprocess, tempfile
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('patch13',HERE/'aplicar-portal.py')
patch=importlib.util.module_from_spec(spec);spec.loader.exec_module(patch)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('portal',type=Path);p.add_argument('--reverter',action='store_true');a=p.parse_args()
 assert(ROOT/'.laboratorio-dados13').is_file(),'exige núcleo candidato'
 target=a.portal.resolve()
 assert str(target).startswith(('/tmp/santafe-apps5-','/var/tmp/santafe-migracao11-')),'somente cópia de homologação'
 assert target.name=='sfdev.fé' and target.is_file() and not a.portal.is_symlink()
 backup=target.with_name('sfdev.dados13-anterior.fé');journal=target.with_name('sfdev.dados13.json')
 os.umask(0o077)
 if a.reverter:
  info=json.loads(journal.read_text())
  assert sha(target)==info['depois'] and sha(backup)==info['antes'],'arquivos mudaram; reversão recusada'
  data=backup.read_bytes()
 else:
  assert not backup.exists() and not journal.exists(),'já preparada; não sobrescrever registro anterior'
  data=target.read_bytes();info={'antes':sha(target)}
 fd,name=tempfile.mkstemp(prefix='.portal13-',suffix='.fé',dir=target.parent);os.close(fd);tmp=Path(name)
 try:
  tmp.write_bytes(data)
  if not a.reverter:patch.corrigir(tmp)
  r=subprocess.run([str(ROOT/'src/santafec'),'-p',str(tmp)],capture_output=True,timeout=30)
  assert r.returncode==0,'portal preparado não compila; original preservado'
  tmp.chmod(target.stat().st_mode&0o777)
  if not a.reverter:
   info['depois']=sha(tmp)
   with backup.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
   with journal.open('x') as f:json.dump(info,f);f.flush();os.fsync(f.fileno())
  with tmp.open('rb') as f:os.fsync(f.fileno())
  os.replace(tmp,target)
  print('PORTAL13_REVERTIDO' if a.reverter else 'PORTAL13_PREPARADO',sha(target))
 finally:tmp.unlink(missing_ok=True)
if __name__=='__main__':main()
