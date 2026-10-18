#!/usr/bin/env python3
"""Confere distribuição, normalização dos caminhos e exclusões de segredos."""
from pathlib import Path
import re
import sys
import tarfile
import unicodedata

with tarfile.open(sys.argv[1]) as archive:
    names = set()
    count = 0
    for member in archive.getmembers():
        name = member.name
        assert name == unicodedata.normalize('NFC', name), 'caminho não normalizado: ' + name
        assert name not in names, 'caminho duplicado: ' + name
        names.add(name)
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
        assert not member.issym() and not member.islnk(), name
        if not member.isfile():
            continue
        count += 1
        path = Path(name)
        assert '.git' not in path.parts and '__pycache__' not in path.parts
        assert not name.endswith(('.env', '.pulso', '.pyc', '.o', '.so', '.key'))
        data = archive.extractfile(member).read()
        if re.search(rb'^-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', data, re.M):
            assert name.endswith('/testes/recursos/tls-local-chave.pem'), name
        assert not re.search(rb'(?:AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{36,})', data), name
    for required in ['docs/manual.html', 'docs/validar-manual.py', 'ferramentas/sls/sls.fé',
                     'testes/recursos/tls-local-certificado.pem', 'testes/recursos/tls-local-chave.pem',
                     'ferramentas/unicode/17.0.0/LICENSE.txt']:
        assert any(name.endswith('/' + required) for name in names), required
print('Distribuição: %d arquivos; caminhos NFC; sem ambientes privados/logs; chave apenas de teste TLS: ok' % count)
