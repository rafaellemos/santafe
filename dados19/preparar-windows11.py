from pathlib import Path
import json,hashlib,shutil,sys,zipfile
root=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve()
dest=out/'entrada-windows11';dest.mkdir()
for source,target in [
 (out/'instalador/santafe-dados19-windows-x64.msi',Path('dados19.msi')),
 (out/'instalador/santafe-dados19-windows-x64.json',Path('dados19.json')),
 (root/'extensões/vscode/api-publica.json',Path('source/extensões/vscode/api-publica.json')),
 (root/'experimentos/dados-v1/testar.fé',Path('source/listas.fé')),
 (root/'experimentos/dados-v1/testar-onfe.fé',Path('source/onfe.fé')),
 (root/'experimentos/dados-v1/onfé.fé',Path('source/experimentos/dados-v1/onfé.fé')),
]:
 p=dest/target;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,p)
shutil.copytree(root/'testes/integracao/sls',dest/'source/testes/integracao/sls',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
shutil.copytree(out/'ferramentas/casos/repo',dest/'repo')
hashes={p.relative_to(dest).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.rglob('*') if p.is_file()}
(dest/'MANIFESTO.json').write_text(json.dumps(hashes,ensure_ascii=True,indent=2),encoding='utf-8')
with zipfile.ZipFile(out/'windows11-input.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
 for p in sorted(dest.rglob('*')):
  if p.is_file():z.write(p,p.relative_to(dest).as_posix())
