#!/usr/bin/env python3
"""Candidato privado derivado da entrega selada dados.11."""
from pathlib import Path
import hashlib,json,shutil,subprocess,tarfile,tempfile
R=Path(__file__).resolve().parents[2]
a=R/'dist/candidato-dados-v11/santafe-candidato-dados.11-fontes.tar.gz'
h='5ff4e9f68f512e964f0401c7722c3fc9581ac74c3bbd99b7587ed4e3018f0c31'
assert hashlib.sha256(a.read_bytes()).hexdigest()==h
s=Path(tempfile.mkdtemp(prefix='santafe-dados12-',dir='/tmp')).resolve()
with tarfile.open(a) as t:
 assert all(m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in t.getmembers())
 t.extractall(s)
for n in ('src/lua.h','ferramentas/sls/sls.fé','docs/manual.html','Makefile','instalar.sh','experimentos/dados-v3/testar-wasm.js','experimentos/dados-v5/testar-instalacao.py','experimentos/dados-v6/testar-operacao.py','experimentos/dados-v6/operacao.py','experimentos/dados-v2/editores.py','experimentos/dados-v2/testar-editores.js','experimentos/dados-v8/testar-editores.js','experimentos/dados-v8/testar-recorte-sublime.py','experimentos/dados-v10/testar.py'):
 p=s/n;p.write_text(p.read_text().replace('dados.11','dados.12').replace('dados-v11/editores','dados-v12/editores').replace('dados-v11/gramaticas-vscode','dados-v12/gramaticas-vscode').replace('0.0.11','0.0.12').replace('EDITORES_DADOS_11_OK','EDITORES_DADOS_12_OK'))
shutil.copytree(R/'experimentos/dados-v12',s/'experimentos/dados-v12',ignore=shutil.ignore_patterns('__pycache__'))
shutil.copytree(s/'experimentos/dados-v11/gramaticas-vscode',s/'experimentos/dados-v12/gramaticas-vscode')
shutil.copyfile(R/'docs/TERMINOLOGIA.md',s/'docs/TERMINOLOGIA.md')
shutil.copyfile(R/'docs/PLANO-PUBLICACAO-CONJUNTA-20261021.md',s/'docs/PLANO-PUBLICACAO-CONJUNTA-20261021.md')
p=s/'docs/manual.html';p.write_text(p.read_text().replace('fallback local','alternativa local').replace('Não significa rollback;','Não significa reversão;'))
(s/'.laboratorio-dados12').write_text('Somente homologação.\n')
shutil.copy2(R/'experimentos/dados-v12/carga-sintetica.py',s/'experimentos/dados-v6/carga.py')
subprocess.run(['python3',s/'experimentos/dados-v12/aplicar.py',s],check=True)
print('CANDIDATO_PREPARADO',s)
