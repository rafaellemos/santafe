"""Catálogo compartilhado: contratos C e Fé do mesmo fonte que o manual."""
import importlib.util
from pathlib import Path
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
def catalogue():
    spec = importlib.util.spec_from_file_location('manual', ROOT / 'docs/validar-manual.py')
    manual = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(manual)
    items = {}
    for source, register, prefix, excluded in manual.CONTRATOS_C:
        for name in manual.funções_do_registro_c(ROOT / source, register):
            if name.startswith('__') or name in excluded:
                continue
            label = unicodedata.normalize('NFC', prefix + name)
            items[label] = {'rótulo': label, 'origem': source, 'categoria': 'API C / núcleo'}
    category = 'Biblioteca Santafé'
    for line in (ROOT / 'docs/API-PUBLICA-FE.tsv').read_text().splitlines():
        line = unicodedata.normalize('NFC', line.strip())
        if not line:
            continue
        if line.startswith('#'):
            category = line[1:].strip()
            continue
        label, source = line.split('|', 1)
        items[label] = {'rótulo': label, 'origem': source, 'categoria': category}
    return sorted(items.values(), key=lambda item: item['rótulo'].casefold())
