#!/usr/bin/env python3
from pathlib import Path
import hashlib,tarfile,tempfile,shutil
R=Path(__file__).resolve().parents[2];archive=R/'dist/candidato-dados-v14/santafe-candidato-dados.14-fontes.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='ddca28b7e058795ab5ff5d15a412ee8517962d421279df3bee20812cca47e5ce'
s=Path(tempfile.mkdtemp(prefix='santafe-dados15-',dir='/tmp')).resolve()
with tarfile.open(archive) as t:
 assert all(m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in t.getmembers());t.extractall(s)
(s/'.laboratorio-dados15').write_text('Somente homologação.\n')
for n in ['src/lua.h','ferramentas/sls/sls.fé','docs/manual.html','Makefile','instalar.sh','experimentos/dados-v3/testar-wasm.js','experimentos/dados-v5/testar-instalacao.py','experimentos/dados-v6/testar-operacao.py','experimentos/dados-v6/operacao.py','experimentos/dados-v2/editores.py','experimentos/dados-v2/testar-editores.js','experimentos/dados-v8/testar-editores.js','experimentos/dados-v8/testar-recorte-sublime.py','experimentos/dados-v10/testar.py']:
 p=s/n;p.write_text(p.read_text().replace('dados.14','dados.15').replace('0.0.14','0.0.15').replace('dados-v14/editores','dados-v15/editores').replace('dados-v14/gramaticas-vscode','dados-v15/gramaticas-vscode').replace('EDITORES_DADOS_14_OK','EDITORES_DADOS_15_OK'))
shutil.copytree(R/'experimentos/dados-v15',s/'experimentos/dados-v15',ignore=shutil.ignore_patterns('__pycache__','LOCAL.json'))
shutil.copytree(s/'experimentos/dados-v14/gramaticas-vscode',s/'experimentos/dados-v15/gramaticas-vscode')
print(s)
