#!/usr/bin/env python3
"""Obtém Pebble público, com digest da release oficial; não instala no sistema."""
from pathlib import Path
import hashlib,json,tarfile,tempfile,urllib.request,shutil,io
ROOT=Path(__file__).resolve().parents[2];assert(ROOT/'.laboratorio-dados13').is_file()
root=Path(tempfile.mkdtemp(prefix='santafe-acme13-',dir='/tmp'));root.chmod(0o700)
def get(url):
 with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Santafe-homologacao'}),timeout=30) as f:return f.read()
release=json.loads(get('https://api.github.com/repos/letsencrypt/pebble/releases/tags/v2.10.1'))
records=[]
for name in ['pebble-linux-amd64.tar.gz','pebble-challtestsrv-linux-amd64.tar.gz']:
 a=next(x for x in release['assets'] if x['name']==name);assert a['size']<5*1024**2
 data=get(a['browser_download_url']);h=hashlib.sha256(data).hexdigest()
 assert a.get('digest')=='sha256:'+h,'digest da release ausente ou divergente'
 with tarfile.open(fileobj=io.BytesIO(data)) as t:
  matches=[m for m in t.getmembers() if m.isfile() and Path(m.name).name in ['pebble','pebble-challtestsrv']]
  assert len(matches)==1
  dest=root/Path(matches[0].name).name;dest.write_bytes(t.extractfile(matches[0]).read());dest.chmod(0o700)
 records.append({'url':a['browser_download_url'],'arquivo_sha256':h,'executavel_sha256':hashlib.sha256(dest.read_bytes()).hexdigest()})
(root/'origens.json').write_text(json.dumps(records,indent=2)+'\n')
print(root)
