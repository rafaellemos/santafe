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
binary = prefix / 'bin/santafé'
version = subprocess.run([str(binary), '-v'], capture_output=True, check=True, timeout=10)
assert b'2.0.2' in version.stdout + version.stderr
source = '; '.join('garanta(importe "%s")' % name for name in
                   ['arquivo', 'rede', 'mariadb', 'segredo', 'tomada', 'correio.imap', 'nomes', 'rpdf', 'vigia'])
subprocess.run([str(binary), '-e', source], env=env, cwd='/tmp', check=True, timeout=10)
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
print('Instalação: versão, bibliotecas e SLS instalado com espaços no caminho: ok')
