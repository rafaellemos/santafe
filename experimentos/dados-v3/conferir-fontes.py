#!/usr/bin/env python3
"""Confere o manifesto do pacote extraído; não instala nem executa Santafé."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
assert (root / '.laboratorio-dados3').is_file(), 'árvore não é o laboratório dados.3'
manifest = json.loads((root / 'MANIFESTO-FONTES.json').read_text())
assert isinstance(manifest, dict) and manifest, 'manifesto vazio ou inválido'
for name, expected in manifest.items():
    relative = Path(name)
    assert not relative.is_absolute() and '..' not in relative.parts, 'caminho inválido'
    path = root / relative
    assert path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(root), name
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, name
print(f'Fontes conferidos: {len(manifest)} arquivos; SHA-256 íntegro.')
