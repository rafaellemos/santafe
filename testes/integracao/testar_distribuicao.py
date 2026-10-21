#!/usr/bin/env python3
"""Confere distribuição, normalização dos caminhos e exclusões de segredos."""
from pathlib import Path
import re
import sys
import tarfile
import unicodedata
import zipfile
import hashlib

with tarfile.open(sys.argv[1]) as archive:
    names = set()
    contents = {}
    count = 0
    for member in archive.getmembers():
        name = member.name
        assert name == unicodedata.normalize('NFC', name), 'caminho não normalizado: ' + name
        assert name not in names, 'caminho duplicado: ' + name
        names.add(name)
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
        assert not member.issym() and not member.islnk(), name
        assert member.isfile() or member.isdir(), 'entrada especial no TAR: ' + name
        if not member.isfile():
            continue
        count += 1
        path = Path(name)
        assert '.git' not in path.parts and '__pycache__' not in path.parts
        assert not name.endswith(('.env', '.pulso', '.pyc', '.o', '.so', '.key'))
        data = archive.extractfile(member).read()
        contents[name] = hashlib.sha256(data).hexdigest()
        if re.search(rb'^-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', data, re.M):
            assert name.endswith('/testes/recursos/tls-local-chave.pem'), name
        assert not re.search(rb'(?:AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{36,})', data), name
    for required in ['docs/manual.html', 'docs/validar-manual.py', 'ferramentas/sls/sls.fé',
                     'ferramentas/sls/analisador.fé', 'ferramentas/sls/nativo.c',
                     'ferramentas/pacotes/cli.fé', 'ferramentas/pacotes/nativo.c',
                     'bibliotecas/catalogo.json',
                     'testes/recursos/temporarios.fé',
                     'extensões/vscode/vendor/vscode-oniguruma/release/onig.wasm',
                     'extensões/vscode/vendor/vscode-oniguruma/LICENSE.txt',
                     'extensões/vscode/vendor/vscode-textmate/LICENSE.md',
                     'testes/recursos/tls-local-certificado.pem', 'testes/recursos/tls-local-chave.pem',
                     'ferramentas/unicode/17.0.0/LICENSE.txt']:
        assert any(name.endswith('/' + required) for name in names), required
    assert not any('/docs/evidencias/' in name for name in names), 'evidências locais no pacote'
    assert not any('/.santafe/' in name for name in names), 'cache privado de projeto no pacote'
if len(sys.argv) > 2:
    with zipfile.ZipFile(sys.argv[2]) as archive:
        assert archive.testzip() is None, 'ZIP corrompido'
        assert len(archive.namelist()) == len(set(archive.namelist())), 'nomes duplicados no ZIP'
        zipped = {item.filename: hashlib.sha256(archive.read(item)).hexdigest()
                  for item in archive.infolist() if not item.is_dir()}
        assert contents == zipped, 'TAR e ZIP devem conter exatamente os mesmos fontes'
    print('TAR e ZIP: conteúdo idêntico')
print('Distribuição: %d arquivos; caminhos NFC; sem ambientes privados/logs; chave apenas de teste TLS: ok' % count)
