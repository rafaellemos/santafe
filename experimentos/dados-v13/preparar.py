#!/usr/bin/env python3
"""Deriva dados.13 exclusivamente dos fontes selados dados.12."""
from pathlib import Path
import hashlib,tarfile,tempfile,shutil
ROOT=Path(__file__).resolve().parents[2]
a=ROOT/'dist/candidato-dados-v12/santafe-candidato-dados.12-fontes.tar.gz'
assert hashlib.sha256(a.read_bytes()).hexdigest()=='1de126f3f0f16dbf21079f39b7f8847b03250178093c446e4e4ba25f0a2ab4e8'
s=Path(tempfile.mkdtemp(prefix='santafe-dados13-',dir='/tmp')).resolve()
with tarfile.open(a) as t:
 assert all(m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in t.getmembers())
 t.extractall(s)
(s/'.laboratorio-dados13').write_text('Somente homologação.\n')
names=['src/lua.h','ferramentas/sls/sls.fé','docs/manual.html','Makefile','instalar.sh','experimentos/dados-v3/testar-wasm.js','experimentos/dados-v5/testar-instalacao.py','experimentos/dados-v6/testar-operacao.py','experimentos/dados-v6/operacao.py','experimentos/dados-v2/editores.py','experimentos/dados-v2/testar-editores.js','experimentos/dados-v8/testar-editores.js','experimentos/dados-v8/testar-recorte-sublime.py','experimentos/dados-v10/testar.py']
for n in names:
 p=s/n;p.write_text(p.read_text().replace('dados.12','dados.13').replace('0.0.12','0.0.13').replace('dados-v12/editores','dados-v13/editores').replace('dados-v12/gramaticas-vscode','dados-v13/gramaticas-vscode').replace('EDITORES_DADOS_12_OK','EDITORES_DADOS_13_OK'))
shutil.copytree(ROOT/'experimentos/dados-v13',s/'experimentos/dados-v13',ignore=shutil.ignore_patterns('__pycache__','LOCAL.json'))
shutil.copytree(s/'experimentos/dados-v12/gramaticas-vscode',s/'experimentos/dados-v13/gramaticas-vscode')
print('CANDIDATO_PREPARADO',s)
