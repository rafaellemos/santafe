#!/usr/bin/env python3
"""Compile the private POSIX support with allocator fault injection/sanitizers."""
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[2]
source=Path(os.environ.get('SANTAFE_TEST_SRC',ROOT/'src'))
with tempfile.TemporaryDirectory(prefix='santafe-pacotes-memoria-') as temporary:
    base=Path(temporary); data=base/'raiz'; data.mkdir(); (data/'origem').write_text('olá\n'*1000)
    command=shlex.split(os.environ.get('CC','cc'))+['-std=c99','-Wall','-Wextra','-I'+str(source)]
    command+=shlex.split(subprocess.check_output(['pkg-config','--cflags','glib-2.0'],text=True))
    command+=shlex.split(os.environ.get('CFLAGS',''))
    command+=[str(ROOT/'testes/integracao/pacotes_memoria.c'),str(ROOT/'ferramentas/pacotes/nativo.c'),str(source/'liblua.a'),'-lm']
    command+=shlex.split(subprocess.check_output(['pkg-config','--libs','glib-2.0'],text=True))
    if sys.platform.startswith('linux'): command+=['-ldl']
    command+=shlex.split(os.environ.get('LDFLAGS',''))+['-o',str(base/'teste')]
    subprocess.run(command,check=True,timeout=60)
    subprocess.run([str(base/'teste'),str(data)],check=True,timeout=90)
