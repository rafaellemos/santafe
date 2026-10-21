"""Catálogo compartilhado: contratos C e Fé do mesmo fonte que o manual."""
import importlib.util
import re
from pathlib import Path
import unicodedata
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[1]

class ManualRows(HTMLParser):
    """Only table signatures and prose; never evaluate examples or HTML."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows, self.cells, self.cell = {}, None, None

    def handle_starttag(self, tag, attrs):
        if tag == 'tr':
            self.cells = []
        elif tag == 'td' and self.cells is not None:
            self.cell = []

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag == 'td' and self.cell is not None:
            self.cells.append(' '.join(''.join(self.cell).split()))
            self.cell = None
        elif tag == 'tr' and self.cells is not None:
            if len(self.cells) >= 2:
                signature = self.cells[0].replace('expand_more', '').strip()
                match = re.match(r'([\w.:]+)\s*\(', signature)
                if match:
                    self.rows.setdefault(unicodedata.normalize('NFC', match[1]),
                                         (signature, self.cells[1]))
            self.cells = self.cell = None

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
    # CJSON registra sua API numa matriz local (com recuo), fora dos registros
    # globais do validador. Ela também integra o núcleo distribuído.
    source = 'src/lua_cjson.c'
    text = (ROOT / source).read_text()
    register = re.search(r'luaL_Reg\s+reg\[\]\s*=\s*\{(.*?)\n\s*\};', text, re.S)
    if register is None:
        raise ValueError('registro público JSON não encontrado')
    names = re.findall(r'\{\s*"((?:\\.|[^"\\])*)"\s*,', register[1])
    body = text[text.index('static int lua_cjson_new(lua_State *l)\n{'):text.index('/* Return cjson.safe module table */')]
    names += re.findall(r'lua_setfield\(l, -2, "((?:\\.|[^"\\])*)"\)', body)
    for name in names:
        label = 'json.' + manual.decodificar_literal_c([name])
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
    rows = ManualRows()
    rows.feed((ROOT / 'docs/manual.html').read_text())
    for label, item in items.items():
        if label in rows.rows:
            item['assinatura'], item['documentação'] = rows.rows[label]
    return sorted(items.values(), key=lambda item: item['rótulo'].casefold())
