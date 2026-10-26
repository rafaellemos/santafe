"""Reutiliza os critérios20 para21, alterando somente identificadores de evidência."""
from pathlib import Path
import shutil
import sys

repo = Path(__file__).resolve().parent.parent
dest = repo/'apoio21'
assert not dest.exists()
shutil.copytree(repo/'dados20', dest, ignore=shutil.ignore_patterns('overlay', 'base', '*.zip'))
changes = {
    'testar.py': [("'candidato':'dados.20'", "'candidato':'dados.21'")],
    'portatil.py': [('dados.20', 'dados.21'), ('santafe-dados20-windows-x64-portatil.zip', 'santafe-dados21-windows-x64-portatil.zip')],
    'recursos.py': [('3.0.20.0', '3.0.21.0'), ('3,0,20,0', '3,0,21,0'), ('dados.20', 'dados.21')],
}
for name, pairs in changes.items():
    p = dest/name; text = p.read_text(encoding='utf-8')
    for old, new in pairs:
        assert old in text, (name, old)
        text = text.replace(old, new)
    p.write_text(text, encoding='utf-8')
original = (repo/'windows/testar.py').read_text(encoding='utf-8')
assert original.count("'candidato':'dados.20'") == 1
(repo/'windows/testar21.py').write_text(original.replace("'candidato':'dados.20'", "'candidato':'dados.21'"), encoding='utf-8')
print('BATERIA21_PREPARADA criterios20 preservados; sem MSI ou publicacao')
