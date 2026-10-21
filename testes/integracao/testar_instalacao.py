#!/usr/bin/env python3
"""Ensaia um prefixo já instalado, sem alterar o sistema."""
import json
import os
from pathlib import Path
import subprocess
import sys

prefix = Path(sys.argv[1]).resolve()
env = dict(os.environ, GSETTINGS_BACKEND='memory',
           LUA_PATH=f'{prefix}/share/santafé/1.0/bibf/?.fé;{prefix}/share/santafé/1.0/bibf/?/?.fé;;',
           LUA_CPATH=f'{prefix}/lib/santafé/1.0/bibc/?.so;;')
env.pop('RPDF_FONTE', None)  # a instalação precisa localizar sua própria fonte
binary = prefix / 'bin/santafé'
version = subprocess.run([str(binary), '-v'], capture_output=True, check=True, timeout=10)
assert b'2.0.2' in version.stdout + version.stderr
source = '; '.join('garanta(importe "%s")' % name for name in
                   ['arquivo', 'rede', 'mariadb', 'segredo', 'tomada', 'correio.imap', 'nomes', 'rpdf', 'vigia'])
subprocess.run([str(binary), '-e', source], env=env, cwd='/tmp', check=True, timeout=10)
font = prefix / 'share/santafé/1.0/bibf/rpdf/fontes/NotoSans-Regular.ttf'
located = subprocess.run([str(binary), '-e',
                          'mostre((importe "rpdf_unicode").localizeFonte())'],
                         env=env, cwd='/tmp', capture_output=True, text=True,
                         check=True, timeout=10)
assert Path(located.stdout.strip()).resolve() == font.resolve(), (
    'RPDF usou fonte fora do prefixo instalado: ' + located.stdout)
subprocess.run([str(binary), '-e', '''local RPDF = importe "rpdf"
local documento = RPDF:novo()
documento:AdicionePágina()
documento:DefinaFonte("notoSans", "", 14)
documento:Célula(0, 10, "Ação — Santafé", 0, 1)
garanta(documento:Saída("", "colar"):corte(1, 8) == "%PDF-2.0")'''],
               env=env, cwd='/tmp', check=True, timeout=10)
messages = [
    {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}},
    {'jsonrpc': '2.0', 'id': 2, 'method': 'shutdown'},
    {'jsonrpc': '2.0', 'method': 'exit'},
]
frames = b''
for message in messages:
    body = json.dumps(message).encode()
    frames += ('Content-Length: %d\r\n\r\n' % len(body)).encode() + body
result = subprocess.run([str(prefix / 'bin/santafé-sls')], input=frames,
                        capture_output=True, cwd='/tmp', check=True, timeout=10)
assert b'Content-Length:' in result.stdout and b'0.1.1' in result.stdout
assert b'"error"' not in result.stdout
print('Instalação: versão, bibliotecas, PDF e SLS com espaços no caminho: ok')
