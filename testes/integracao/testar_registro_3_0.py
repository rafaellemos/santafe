#!/usr/bin/env python3
"""Confere o código executável do Git contra a fonte 3.0 já distribuída.

Testes, CI e notas de registro são mantidos depois do fechamento do TAR.
O manifesto original não é reescrito para fingir igualdade dos pacotes.
"""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
manifest = json.loads((ROOT / 'MANIFESTO-FONTES.json').read_text())
assert len(manifest) == 920
prefixes = ('src/', 'bibs/', 'ferramentas/', 'aplicativos/')
checked = 0
for name, expected in manifest.items():
    if not name.startswith(prefixes) or '/testes/' in name:
        continue
    path = ROOT / name
    assert path.is_file() and not path.is_symlink(), name
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, name
    checked += 1
assert checked > 300
for name in ('lua.h', 'luaconf.h', 'lauxlib.h', 'lualib.h', 'lua.hpp'):
    assert (ROOT / 'include' / name).read_bytes() == (ROOT / 'src' / name).read_bytes(), name
version = subprocess.run([str(ROOT/'src/santafé'), '-v'], capture_output=True, check=True)
assert b'3.0.0' in version.stdout + version.stderr
assert json.loads((ROOT/'extensões/vscode/package.json').read_text())['version'] == '2.0.0'
# Revisão independente do editor; os fontes de execução 3.0 acima continuam imutáveis.
assert json.loads((ROOT/'extensões/sublime/package-metadata.json').read_text())['version'] == '2.0.1'
assert hashlib.sha256((ROOT/'testes/windows/baseline-dados16.zip').read_bytes()).hexdigest() == '84be8651b8e41787524f4be13ce27a6d3a9be185a3f12537891e2108773a26a4'
print(f'Registro 3.0: {checked} fontes de execução idênticos à distribuição; SDK e editores coerentes')
