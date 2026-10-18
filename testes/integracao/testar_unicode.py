#!/usr/bin/env python3
"""Verifica cada fronteira dos testes oficiais Unicode, no núcleo real."""
from pathlib import Path
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
binary = os.environ.get('SANTAFE_TEST_BIN', str(ROOT / 'src/santafé'))
data = ROOT / 'ferramentas/unicode/17.0.0/GraphemeBreakTest.txt'
source = []
cases = boundaries = 0
for line in data.read_text(encoding='utf-8').splitlines():
    fields = line.split('#')[0].split()
    if not fields:
        continue
    cases += 1
    text = b''
    count = 0
    for i in range(1, len(fields), 2):
        count += fields[i - 1] == '÷'
        text += chr(int(fields[i], 16)).encode('utf-8')
        escaped = ''.join('\\%03d' % b for b in text)
        source.append('garanta(tamanho("%s") == %d, "Unicode caso %d posição %d")' % (escaped, count, cases, i))
        source.append('garanta(colar.tamanho("%s") == %d)' % (escaped, count))
        boundaries += 1
for bad in [b'\x80', b'\xc0\x80', b'\xe0\x80\x80', b'\xed\xa0\x80', b'\xf4\x90\x80\x80', b'\xf0\x9f', b'\xff']:
    escaped = ''.join('\\%03d' % b for b in bad)
    source.append('garanta(não proteja(tamanho, "%s"))' % escaped)
source.append('garanta(tamanho("") == 0)')
with tempfile.TemporaryDirectory(prefix='santafe-unicode-') as folder:
    script = Path(folder) / 'unicode.fé'
    script.write_text('\n'.join(source), encoding='utf-8')
    subprocess.run([binary, str(script)], check=True, timeout=30)
print('Unicode 17.0.0: %d casos, %d fronteiras, UTF-8 inválido: ok' % (cases, boundaries))
