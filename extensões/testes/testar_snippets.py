"""Os modelos inseridos pelos editores devem compilar no núcleo real."""
import json
from pathlib import Path
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
items=[]
for name,s in json.loads((ROOT/'extensões/vscode/snippets/santafe.code-snippets').read_text()).items():
    items.append(('VSCode '+name,'\n'.join(s['body']) if isinstance(s['body'],list) else s['body']))
for f in (ROOT/'extensões/sublime/snippets').glob('*.sublime-snippet'):
    items.append(('Sublime '+f.name,ET.parse(f).findtext('content')))
with tempfile.TemporaryDirectory(prefix='santafe-snippets-') as temp:
    for name,text in items:
        text=re.sub(r'\$\{\d+(?::([^}]*))?\}',lambda m:m[1] or '',text)
        text=re.sub(r'\$\d+','',text)
        source=Path(temp)/'snippet.fé'
        source.write_text(text)
        r=subprocess.run([str(ROOT/'src/santafec'),'-p',str(source)],capture_output=True,text=True)
        assert r.returncode==0,(name,text,r.stderr)
print(f'Snippets: {len(items)} modelos compilados pelo núcleo real: ok')
