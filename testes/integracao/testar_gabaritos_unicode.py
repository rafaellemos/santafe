#!/usr/bin/env python3
"""Executa no núcleo nomes NFC/NFD, limites UTF-8 e bytecode, sob locale C."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
BIN = os.environ.get('SANTAFE_TEST_BIN', str(ROOT / 'src/santafé'))
COMPILER = os.environ.get('SANTAFE_TEST_COMPILER', str(ROOT / 'src/santafec'))
names = set(json.loads((ROOT / 'extensões/testes/identificadores-unicode.json').read_text(encoding='utf-8')))
for point in range(0xC0, 0x250):
    letter = chr(point)
    if unicodedata.category(letter).startswith('L'):
        for form in ('NFC', 'NFD'):
            name = unicodedata.normalize(form, letter)
            names.update((name + 'nome', 'a' + name + '_2'))


def quoted(data):
    if isinstance(data, str):
        data = data.encode('utf-8')
    return '"' + ''.join('\\%03d' % b for b in data) + '"'


source = []
for index, name in enumerate(sorted(names)):
    # Escopos separados não excedem o limite de variáveis locais por função.
    for declaration in ('local ', ''):
        source.append('(função() %s%s = "VALOR"' % (declaration, name))
        for mark in ('®', 'Ⓡ'):
            source.append('garanta(`%s%s!` == "VALOR!", "caso %d")' % (mark, name, index))
            source.append('garanta(`%s{%s}` == "VALOR")' % (mark, name))
            source.append('garanta(`\\%s%s` == %s)' % (mark, name, quoted(mark + name)))
        if not declaration:
            source.append('%s = nulo' % name)
        source.append('fim)();')

# Bytes malformados, NUL, sinais, emoji e marcas órfãs nunca viram um nome.
for mark in ('®', 'Ⓡ'):
    for bad in (b'\x80', b'\xc0\x80', b'\xe0\x80\x80', b'\xed\xa0\x80',
                b'\xf4\x90\x80\x80', b'\xf0\x9f', b'\xff', b'\0',
                '—'.encode(), '🟢'.encode(), '«'.encode(), b'9'):
        value = mark.encode() + bad
        source.append('garanta(__gabarito(%s) == %s);' % (quoted(value), quoted(value)))
    for bad in (b'\x80', b'\xc0\x80', b'\xe0\x80\x80', b'\xed\xa0\x80',
                b'\xf4\x90\x80\x80', b'\xf0\x9f', b'\xff', b'\0',
                '—'.encode(), '🟢'.encode(), '«'.encode()):
        source.append('(função() local ação="V"; garanta(__gabarito(%s) == %s) fim)();' % (
            quoted((mark + 'ação').encode() + bad), quoted(b'V' + bad)))

long_name = 'ação_' + 'á' * 4096
source.append('(função() local %s="LONGO"; garanta(`®%s Ⓡ%s` == "LONGO LONGO") fim)();' % (
    long_name, long_name, long_name))
env = dict(os.environ, LC_ALL='C')
with tempfile.TemporaryDirectory(prefix='santafe-gabaritos-') as folder:
    script = Path(folder) / 'unicode.fé'
    script.write_text('\n'.join(source), encoding='utf-8')
    subprocess.run([BIN, str(script)], env=env, check=True, timeout=30)
    compiled = Path(folder) / 'unicode.compilado'
    subprocess.run([COMPILER, '-o', str(compiled), str(script)], env=env, check=True, timeout=30)
    subprocess.run([BIN, str(compiled)], env=env, check=True, timeout=30)
print('Gabaritos Unicode: %d nomes, locais/globais, dois curingas, fonte/bytecode, UTF-8 inválido: ok' % len(names))
