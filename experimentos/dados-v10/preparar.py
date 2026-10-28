#!/usr/bin/env python3
"""Deriva a revisão de IBA do arquivo imutável dados.9."""
from pathlib import Path
import hashlib,json,shutil,subprocess,tarfile,tempfile
R=Path(__file__).resolve().parents[2]
archive=R/'dist/candidato-dados-v9/santafe-candidato-dados.9-fontes.tar.gz'
expected='59cecf0965e3ce5f25a21c667faaea94c689f7fe90bc70632dd6458bb7c3c253'
assert hashlib.sha256(archive.read_bytes()).hexdigest()==expected
s=Path(tempfile.mkdtemp(prefix='santafe-dados10-',dir='/tmp')).resolve()
with tarfile.open(archive) as pack:
 for m in pack.getmembers():
  if not m.isfile() or Path(m.name).is_absolute() or '..' in Path(m.name).parts:raise SystemExit('Membro inválido')
 pack.extractall(s)
subprocess.run(['python3',s/'experimentos/dados-v3/conferir-fontes.py'],check=True)
before=json.loads((s/'MANIFESTO-FONTES.json').read_text())
for n in ('src/lua.h','ferramentas/sls/sls.fé','docs/manual.html','Makefile','instalar.sh','experimentos/dados-v3/testar-wasm.js','experimentos/dados-v5/testar-instalacao.py','experimentos/dados-v6/testar-operacao.py','experimentos/dados-v6/operacao.py'):
 p=s/n;p.write_text(p.read_text().replace('dados.9','dados.10'))
for n in ('experimentos/dados-v2/editores.py','experimentos/dados-v2/testar-editores.js','experimentos/dados-v8/testar-editores.js','experimentos/dados-v8/testar-recorte-sublime.py'):
 p=s/n;p.write_text(p.read_text().replace('dados-v9/editores','dados-v10/editores').replace('dados.9','dados.10').replace('0.0.9','0.0.10').replace('EDITORES_DADOS_9_OK','EDITORES_DADOS_10_OK'))
shutil.copytree(R/'experimentos/dados-v10',s/'experimentos/dados-v10',ignore=shutil.ignore_patterns('__pycache__'))
(s/'.laboratorio-dados10').write_text('Somente homologação; nenhuma instalação em produção.\n')
subprocess.run(['python3',s/'experimentos/dados-v10/aplicar.py',s],check=True)
subprocess.run(['python3',s/'experimentos/dados-v10/documentar.py',s],check=True)
changes=[{'arquivo':n,'antes':sha,'depois':hashlib.sha256((s/n).read_bytes()).hexdigest()} for n,sha in before.items() if (s/n).is_file() and hashlib.sha256((s/n).read_bytes()).hexdigest()!=sha]
(s/'DELTA-DADOS10.json').write_text(json.dumps({'base_sha256':expected,'alterados':changes},ensure_ascii=False,indent=2)+'\n')
print('CANDIDATO_PREPARADO',s)
