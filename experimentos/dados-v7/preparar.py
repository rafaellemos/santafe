#!/usr/bin/env python3
"""dados.7 é uma derivação conferida de dados.6, nunca da produção."""
from pathlib import Path
import hashlib, shutil, subprocess, tarfile, tempfile
ROOT=Path(__file__).resolve().parents[2]
archive=ROOT/'dist/candidato-dados-v6/santafe-candidato-dados.6-fontes.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='ee649d1cce627853e7f561579480e25d2021a835e54c34858bb6d4a7ef8083e6'
stage=Path(tempfile.mkdtemp(prefix='santafe-dados7-',dir='/tmp'))
with tarfile.open(archive) as pack:
    for m in pack.getmembers():
        assert m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts
    pack.extractall(stage)
subprocess.run(['python3',str(stage/'experimentos/dados-v3/conferir-fontes.py')],check=True)
shutil.copytree(ROOT/'experimentos/dados-v7',stage/'experimentos/dados-v7',ignore=shutil.ignore_patterns('__pycache__'))
shutil.copy2(ROOT/'docs/PLANO-PUBLICACAO-CONJUNTA-20261021.md',stage/'docs/PLANO-PUBLICACAO-CONJUNTA-20261021.md')
for name in ('src/lua.h','ferramentas/sls/sls.fé','Makefile','instalar.sh',
             'experimentos/dados-v3/testar-wasm.js','experimentos/dados-v5/testar-instalacao.py'):
    p=stage/name; p.write_text(p.read_text().replace('dados.6','dados.7'))
(stage/'.laboratorio-dados7').write_text('candidato isolado; não instalar em produção\n')
subprocess.run(['python3',str(stage/'experimentos/dados-v7/aplicar.py')],check=True)
print(stage)
