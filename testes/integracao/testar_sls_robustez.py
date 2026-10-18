#!/usr/bin/env python3
"""Ciclo JSON-RPC/LSP, entradas inválidas e EOF com limite de execução."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BIN = os.environ.get('SANTAFE_TEST_BIN', str(ROOT / 'src/santafé'))
def frame(message):
    content = message if isinstance(message, bytes) else json.dumps(message, ensure_ascii=False).encode()
    return b'Content-Length:\t' + str(len(content)).encode() + b'\r\n\r\n' + content
def req(method, id=None, params=None):
    result = dict(jsonrpc='2.0', method=method, params={} if params is None else params)
    if id is not None:
        result['id'] = id
    return result
def run(messages, code=0):
    process = subprocess.run([BIN, str(ROOT / 'ferramentas/sls/sls.fé')],
                             input=b''.join(frame(m) for m in messages), capture_output=True, timeout=10)
    assert process.returncode == code, process.stderr.decode(errors='replace')
    data = process.stdout
    replies = []
    while data:
        header, data = data.split(b'\r\n\r\n', 1)
        length = int(header.split(b':')[1])
        replies.append(json.loads(data[:length]))
        data = data[length:]
    return replies
messages = [req('unknown', 10), b'{', req('initialize', 11), req('initialize', 12),
            req('textDocument/didChange', params={'textDocument': {'uri': 'file:///teste.fé'}, 'contentChanges': [False]}),
            req('textDocument/didOpen', params=False), req('unknown', 13, False),
            req('shutdown', 14), req('unknown', 15), req('exit')]
replies = run(messages)
assert [r.get('error', {}).get('code') for r in replies] == [-32002, -32700, None, -32600, -32602, None, -32600], replies
assert run([req('exit')], code=1) == []
for bad in [b'x'*8193, b'Content-Length: 16777217\r\n\r\n', b'Content-Length: 2\r\n\r\n{', b'Content-Length: 1\r\nContent-Length: 1\r\n\r\n0']:
    process = subprocess.run([BIN, str(ROOT / 'ferramentas/sls/sls.fé')], input=bad,
                             capture_output=True, timeout=10)
    assert process.returncode == 1, process.stderr
print('SLS robustez e ciclo de vida: ok')
