#!/usr/bin/env python3
"""Pacote de fontes verificável/reproduzível; exclui binários, ambientes e logs."""
from pathlib import Path
import gzip,hashlib,json,sys,tarfile,unicodedata
stage=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve()
if not (stage/'.laboratorio-dados10').is_file() or out.exists():raise SystemExit('Exige laboratório novo e destino inexistente')
roots={'src','bibs','testes','exemplos','aplicativos','ferramentas','experimentos','docs','extensões','bibliotecas','operação'}
single={'LICENSE','Makefile','instalar.sh','DELTA-DADOS10.json'}
files={}
for p in sorted(stage.rglob('*')):
 if not p.is_file() or p.is_symlink():continue
 rel=p.relative_to(stage)
 if rel.parts[0] not in roots and rel.name not in single and not rel.name.startswith(('.laboratorio-dados','MIGRACAO')):continue
 if any(x in {'__pycache__','node_modules','.git','dist','evidencias-host'} for x in rel.parts):continue
 if p.name!='onig.wasm' and p.suffix in {'.o','.a','.so','.dylib','.dll','.pyc','.wasm','.vsix','.sublime-package','.tmp','.env'}:continue
 if p.name in {'santafé','santafec','santafe.js','sls_nativo.c'}:continue
 name=unicodedata.normalize('NFC',str(rel))
 if name in files:raise SystemExit('Colisão de nomes '+name)
 files[name]=p
manifest={n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in files.items()}
(stage/'MANIFESTO-FONTES.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
files['MANIFESTO-FONTES.json']=stage/'MANIFESTO-FONTES.json'
with out.open('xb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as gz,tarfile.open(fileobj=gz,mode='w',format=tarfile.USTAR_FORMAT) as pack:
 for name,p in files.items():
  info=pack.gettarinfo(str(p),arcname=name);info.uid=info.gid=0;info.uname=info.gname='';info.mtime=0
  with p.open('rb') as f:pack.addfile(info,f)
print(hashlib.sha256(out.read_bytes()).hexdigest(),out,len(manifest),'fontes')
