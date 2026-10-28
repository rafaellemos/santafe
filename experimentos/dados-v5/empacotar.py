#!/usr/bin/env python3
"""Pacote verificável de fontes candidatas; nunca produz binário público."""
import hashlib
import json
from pathlib import Path
import sys
import tarfile
import unicodedata

stage=Path(sys.argv[1]).resolve(); output=Path(sys.argv[2]).resolve()
assert (stage/'.laboratorio-dados5').is_file()
assert not output.exists(), 'preserve o pacote anterior'
roots={'src','bibs','testes','exemplos','aplicativos','ferramentas','experimentos',
       'docs','extensões','bibliotecas','operação'}
single={'.laboratorio-dados3','.laboratorio-dados4','.laboratorio-dados5',
        'MIGRACAO.json','MIGRACAO-CADEIA.json','MIGRACAO-APLICATIVOS.json','LICENSE','Makefile','instalar.sh'}
files={}
for p in sorted(stage.rglob('*')):
    if not p.is_file() or p.is_symlink(): continue
    rel=p.relative_to(stage)
    if rel.parts[0] not in roots and str(rel) not in single: continue
    if any(x in {'__pycache__','node_modules','.git','dist'} for x in rel.parts): continue
    if p.suffix in {'.o','.a','.so','.dylib','.dll','.pyc','.wasm','.vsix','.sublime-package','.tmp','.env'}: continue
    if p.name in {'santafé','santafec','santafe.js','sls_nativo.c'}: continue
    name=str(rel)
    assert name==unicodedata.normalize('NFC',name),name
    files[name]=p
manifest={name:hashlib.sha256(p.read_bytes()).hexdigest() for name,p in files.items()}
(stage/'MANIFESTO-FONTES.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
with tarfile.open(output,'w:gz',format=tarfile.USTAR_FORMAT) as package:
    for name,p in files.items():
        info=package.gettarinfo(str(p),arcname=name); info.uid=info.gid=0; info.uname=info.gname='';info.mtime=0
        with p.open('rb') as f: package.addfile(info,f)
    package.add(stage/'MANIFESTO-FONTES.json',arcname='MANIFESTO-FONTES.json',recursive=False)
print(hashlib.sha256(output.read_bytes()).hexdigest(),output)
print(len(files),'arquivos de fonte')
