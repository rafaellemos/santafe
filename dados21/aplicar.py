"""Sobrepõe somente os seis arquivos conferidos, após a base candidata dados20."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys

here = Path(__file__).resolve().parent
root = Path(sys.argv[1]).resolve()
assert (root/'DADOS20-WINDOWS.json').is_file(), 'base dados20 não preparada'
manifest = json.loads((here/'overlay.json').read_text(encoding='utf-8'))
assert set(manifest) == {'src/lua.h', 'src/lwinconsole.h', 'src/santafe.c',
                         'src/lwininput.h', 'src/lauxlib.c', 'src/liolib.c'}
checked = {}
for name, digest in manifest.items():
    assert not PurePosixPath(name).is_absolute() and '..' not in PurePosixPath(name).parts
    data = (here/'overlay'/name).read_bytes()
    assert hashlib.sha256(data).hexdigest() == digest, name
    checked[name] = data
for name, data in checked.items():
    (root/name).write_bytes(data)
(root/'DADOS21-CONSOLE.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
print('DADOS21_CONSOLE_PREPARADO', len(checked))
