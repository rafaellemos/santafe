#!/usr/bin/env python3
"""Deriva o candidato de migração da entrega selada dados.10, sem produção."""
from pathlib import Path
import hashlib,json,shutil,subprocess,tarfile,tempfile
R=Path(__file__).resolve().parents[2]
archive=R/'dist/candidato-dados-v10/santafe-candidato-dados.10-fontes.tar.gz'
expected='0098b7388db7b851c00137e89ec3240f9be2b7f3e20b2bb4cd6ed00a4581af3a'
assert hashlib.sha256(archive.read_bytes()).hexdigest()==expected
s=Path(tempfile.mkdtemp(prefix='santafe-dados11-',dir='/tmp')).resolve()
with tarfile.open(archive) as pack:
 for m in pack.getmembers():
  assert m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts
 pack.extractall(s)
subprocess.run(['python3',s/'experimentos/dados-v3/conferir-fontes.py'],check=True)
before=json.loads((s/'MANIFESTO-FONTES.json').read_text())
for n in ('src/lua.h','ferramentas/sls/sls.fé','docs/manual.html','Makefile','instalar.sh','experimentos/dados-v3/testar-wasm.js','experimentos/dados-v5/testar-instalacao.py','experimentos/dados-v6/testar-operacao.py','experimentos/dados-v6/operacao.py'):
 p=s/n;p.write_text(p.read_text().replace('dados.10','dados.11'))
for n in ('experimentos/dados-v2/editores.py','experimentos/dados-v2/testar-editores.js','experimentos/dados-v8/testar-editores.js','experimentos/dados-v8/testar-recorte-sublime.py','experimentos/dados-v10/testar.py'):
 p=s/n;p.write_text(p.read_text().replace('dados-v10/editores','dados-v11/editores').replace('dados-v10/gramaticas-vscode','dados-v11/gramaticas-vscode').replace('dados.10','dados.11').replace('0.0.10','0.0.11').replace('EDITORES_DADOS_10_OK','EDITORES_DADOS_11_OK'))
shutil.copytree(R/'experimentos/dados-v11',s/'experimentos/dados-v11',ignore=shutil.ignore_patterns('__pycache__'))
shutil.copyfile(R/'docs/PLANO-PUBLICACAO-CONJUNTA-20261021.md',s/'docs/PLANO-PUBLICACAO-CONJUNTA-20261021.md')
shutil.copytree(s/'experimentos/dados-v10/gramaticas-vscode',s/'experimentos/dados-v11/gramaticas-vscode')
(s/'.laboratorio-dados11').write_text('Somente homologação; sem instalação em produção.\n')
changes=[{'arquivo':n,'antes':sha,'depois':hashlib.sha256((s/n).read_bytes()).hexdigest()} for n,sha in before.items() if (s/n).is_file() and hashlib.sha256((s/n).read_bytes()).hexdigest()!=sha]
(s/'DELTA-DADOS11.json').write_text(json.dumps({'base_sha256':expected,'alterados':changes},ensure_ascii=False,indent=2)+'\n')
print('CANDIDATO_PREPARADO',s)
