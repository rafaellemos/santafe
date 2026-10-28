#!/usr/bin/env python3
"""Pacote de fontes de laboratório, não distribuição/instalador público."""
import hashlib
import json
from pathlib import Path
import sys
import tarfile
import unicodedata

stage=Path(sys.argv[1]).resolve(); output=Path(sys.argv[2]).resolve()
assert (stage/'.laboratorio-dados4').is_file()
assert not output.exists(), 'preservar os pacotes anteriores'
roots={'src','bibs','testes','exemplos','aplicativos','ferramentas','experimentos',
       'docs','extensões','bibliotecas','operação'}
single={'.laboratorio-dados3','.laboratorio-dados4','MIGRACAO.json','MIGRACAO-CADEIA.json','LICENSE'}
files={}
for p in sorted(stage.rglob('*')):
    if not p.is_file() or p.is_symlink(): continue
    rel=p.relative_to(stage)
    if rel.parts[0] not in roots and str(rel) not in single: continue
    if any(x in {'__pycache__','node_modules','.git','dist'} for x in rel.parts): continue
    if p.suffix in {'.o','.a','.so','.dylib','.dll','.pyc','.wasm','.vsix','.sublime-package','.tmp'}: continue
    if p.name in {'santafé','santafec','santafe.js','sls_nativo.c'}: continue
    name=str(rel)
    assert name==unicodedata.normalize('NFC',name),name
    files[name]=p
manifest={name:hashlib.sha256(p.read_bytes()).hexdigest() for name,p in files.items()}
(stage/'MANIFESTO-FONTES.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
with tarfile.open(output,'w:gz') as package:
    for name,p in files.items(): package.add(p,arcname=name,recursive=False)
    package.add(stage/'MANIFESTO-FONTES.json',arcname='MANIFESTO-FONTES.json',recursive=False)
print(hashlib.sha256(output.read_bytes()).hexdigest(),output)
print(len(files),'arquivos de fonte')
