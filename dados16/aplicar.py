from pathlib import Path
import hashlib,json,shutil,sys
here=Path(__file__).resolve().parent
root=Path(sys.argv[1]).resolve()
assert (root/'PREPARACAO-WINDOWS.json').is_file()
manifest=json.loads((here/'overlay.json').read_text())
changes={}
for name,digest in manifest.items():
 p=here/'overlay'/name;data=p.read_bytes();assert hashlib.sha256(data).hexdigest()==digest
 target=root/name;before=hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None
 target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
 changes[name]={'antes':before,'depois':digest}
(root/'DADOS16-WINDOWS.json').write_text(json.dumps(changes,indent=2))
print('DADOS16_OVERLAY_CONFERIDO',len(changes))
