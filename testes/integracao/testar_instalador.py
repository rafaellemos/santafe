#!/usr/bin/env python3
"""Falha de instalação nunca pode virar sucesso; não instala nada no sistema."""
from pathlib import Path
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory(prefix='santafe-instalador-') as folder:
    tools = Path(folder)
    for name, content in {'make': '#!/bin/sh\nexit 37\n', 'sudo': '#!/bin/sh\nexec "$@"\n'}.items():
        script = tools / name
        script.write_text(content)
        script.chmod(0o755)
    env = dict(os.environ, PATH=str(tools) + os.pathsep + os.environ['PATH'])
    result = subprocess.run(['bash', str(ROOT / 'instalar.sh'), '--sem-dependencias', '--prefixo', str(tools / 'prefixo')],
                            cwd=folder, env=env, capture_output=True, timeout=10)
    assert result.returncode == 37, result.stdout + result.stderr
    assert b'Instala\xc3\xa7\xc3\xa3o conclu\xc3\xadda' not in result.stdout
    result = subprocess.run(['bash', str(ROOT / 'ferramentas/instalar-arquivos.sh'), 'bin', str(tools / 'prefixo')],
                            cwd=folder, capture_output=True, timeout=10)
    assert result.returncode != 0, 'fontes ausentes não podem ser ignorados'
    prefix = tools / 'prefixo com espaços'
    for relative in ['bin/santafé', 'bin/santafec', 'bin/santafé-sls',
                     'include/lua.h', 'include/lauxlib.h', 'lib/liblua.a',
                     'share/santafé/1.0/ferramentas/sls.fé', 'bin/arquivo-do-usuario']:
        target = prefix / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('apenas teste')
    subprocess.run(['bash', str(ROOT / 'ferramentas/desinstalar-arquivos.sh'), 'bin', str(prefix)],
                   check=True, timeout=10)
    assert (prefix / 'bin/arquivo-do-usuario').exists()
    assert not (prefix / 'bin/santafec').exists()
    assert not (prefix / 'include/lauxlib.h').exists()
    subprocess.run(['bash', str(ROOT / 'ferramentas/instalar-arquivos.sh'), 'pc', str(prefix), 'macosx', '2.0.2'],
                   check=True, timeout=10)
    assert 'Version: 2.0.2' in (prefix / 'lib/pkgconfig/santafe.pc').read_text()
print('Instalador: erros propagados e execução fora da raiz: ok')
print('Desinstalador: destinos individuais e arquivos de terceiros preservados: ok')
