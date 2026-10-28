#!/usr/bin/env python3
"""Isola temporários MariaDB; não muda servidores operacionais."""
from pathlib import Path
import sys
s=Path(sys.argv[1]).resolve();assert(s/'.laboratorio-dados12').is_file()
p=s/'experimentos/dados-v5/laboratorio.py';t=p.read_text()
if 'self.dbtmp' not in t:
 t=t.replace("        self.sock = self.path/'m.sock'", "        self.sock = self.path/'m.sock'\n        self.dbtmp = self.path/'temporarios-db'\n        self.dbtmp.mkdir(mode=0o700)")
 t=t.replace("'--no-defaults', f'--datadir={self.path}/dados'", "'--no-defaults', f'--tmpdir={self.dbtmp}', f'--datadir={self.path}/dados'")
 t=t.replace("f'--datadir={self.path}/dados', f'--socket={self.sock}'", "f'--tmpdir={self.dbtmp}', f'--datadir={self.path}/dados', f'--socket={self.sock}'")
 t=t.replace("        self.wait(p, dbport, 'mariadb')", "        self.wait(p, dbport, 'mariadb')\n        assert Path(self.sql('SELECT @@tmpdir;', False)).resolve()==self.dbtmp.resolve()")
 p.write_text(t)
p=s/'testes/integracao/testar_correio_mariadb.sh';t=p.read_text()
if '--tmpdir=' not in t:
 t=t.replace('"$MARIADB_INSTALAR" --no-defaults', 'mkdir -m 700 "$TEMPORARIO/temporarios-db"\n\n"$MARIADB_INSTALAR" --no-defaults --tmpdir="$TEMPORARIO/temporarios-db"')
 t=t.replace('"$MARIADBD" --no-defaults --datadir=', '"$MARIADBD" --no-defaults --tmpdir="$TEMPORARIO/temporarios-db" --datadir=')
 p.write_text(t)
for n in ['experimentos/dados-v12/carga-replica.py','experimentos/dados-v12/migrar-replica.py','experimentos/dados-v12/restaurar-replica.py']:
 p=s/n
 if not p.exists():continue
 t=p.read_text()
 if "--tmpdir=" not in t:
  if n.endswith('carga-replica.py'):
   t=t.replace('  self.dbport=13306', "  (self.lab/'temporarios-db12').mkdir(mode=0o700,exist_ok=True)\n  self.dbport=13306")
  elif n.endswith('migrar-replica.py'):
   t=t.replace(' def database(self):'," def database(self):\n  (self.lab/'temporarios-db12').mkdir(mode=0o700,exist_ok=True)")
  else:
   t=t.replace(" (lab/'exportacao').mkdir()", " (lab/'temporarios-db12').mkdir(mode=0o700)\n (lab/'exportacao').mkdir()")
  t=t.replace("'--datadir='+str(self.lab/'dados')", "'--tmpdir='+str(self.lab/'temporarios-db12'),'--datadir='+str(self.lab/'dados')")
  t=t.replace("'--datadir='+str(lab/'dados')", "'--tmpdir='+str(lab/'temporarios-db12'),'--datadir='+str(lab/'dados')")
  if n.endswith('carga-replica.py'):
   t=t.replace('  self.wait(p,13306)',"  self.wait(p,13306)\n  M.ensure(Path(self.sql('SELECT @@tmpdir;').strip()).resolve()==(self.lab/'temporarios-db12').resolve(),'temporários não isolados')")
  p.write_text(t)
print('TEMPORARIOS_MARIADB_ISOLADOS')
