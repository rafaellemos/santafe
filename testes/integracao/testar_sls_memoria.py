#!/usr/bin/env python3
"""Pode usar SANTAFE_TEST_SRC instrumentado e CFLAGS/LDFLAGS de sanitizadores."""
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[2]
source=Path(os.environ.get('SANTAFE_TEST_SRC',ROOT/'src'))
with tempfile.TemporaryDirectory(prefix='santafe-sls-memoria-') as temporary:
    base=Path(temporary); data=base/'raiz'; data.mkdir()
    (data/'teste.fé').write_text('local texto="olá"\n'*100)
    nested=data
    for i in range(12):
        nested=nested/f'diretorio{i}'; nested.mkdir()
        (nested/'fonte.fé').write_text('local x=1')
    binary=base/'teste'
    command=shlex.split(os.environ.get('CC','cc'))+['-std=c99','-Wall','-Wextra','-Werror','-I'+str(source)]
    command+=shlex.split(os.environ.get('CFLAGS',''))
    command+=[str(ROOT/'testes/integracao/sls/lexemas_memoria.c'),str(ROOT/'ferramentas/sls/nativo.c'),str(source/'liblua.a'),'-lm']
    if sys.platform.startswith('linux'): command+=['-ldl']
    command+=shlex.split(os.environ.get('LDFLAGS',''))+['-o',str(binary)]
    subprocess.run(command,check=True,timeout=60)
    subprocess.run([str(binary),str(data)],check=True,timeout=60)
