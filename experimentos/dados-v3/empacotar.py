#!/usr/bin/env python3
"""Fontes do laboratório, sem executáveis do hospedeiro nem dados de bancos."""
import hashlib
import json
from pathlib import Path
import sys
import tarfile

stage=Path(sys.argv[1]).resolve()
assert (stage/'.laboratorio-dados3').is_file()
output=Path(sys.argv[2]).resolve()
assert not output.exists(), 'não sobrescrever um pacote anterior'
allowed={'src','bibs','testes','exemplos','aplicativos','ferramentas','experimentos','docs','extensões'}
files=[]
for path in sorted(stage.rglob('*')):
    if not path.is_file() or path.is_symlink(): continue
    rel=path.relative_to(stage)
    if rel.parts[0] not in allowed and str(rel) not in {'.laboratorio-dados3','MIGRACAO.json'}: continue
    if any(p in {'__pycache__','node_modules','.git','dist'} for p in rel.parts): continue
    if path.suffix in {'.o','.a','.so','.dylib','.dll','.pyc','.wasm','.vsix','.sublime-package'}: continue
    if path.name in {'santafé','santafec','santafe.js','santafe.wasm','sls_nativo.c'}: continue
    files.append(path)
manifest={str(p.relative_to(stage)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
(stage/'MANIFESTO-FONTES.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
with tarfile.open(output,'w:gz') as tar:
    for p in files+[stage/'MANIFESTO-FONTES.json']:
        tar.add(p,arcname=str(p.relative_to(stage)),recursive=False)
print(hashlib.sha256(output.read_bytes()).hexdigest(),output)
print(len(manifest),'fontes')
