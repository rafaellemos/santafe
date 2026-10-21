#!/usr/bin/env python3
"""Compila um consumidor isolado da nova API, sem instalar arquivos."""
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile

raiz = Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory(prefix="sls-api-c-") as pasta:
    binario = str(Path(pasta) / "teste")
    comando = shlex.split(os.environ.get("CC", "cc"))
    comando += ["-std=c99", "-Wall", "-Wextra", "-Werror", "-I" + str(raiz / "src"),
                str(raiz / "testes/integracao/sls/analise_c.c"), str(raiz / "src/liblua.a"),
                "-lm", "-o", binario]
    if sys.platform.startswith("linux"):
        comando.append("-ldl")
    subprocess.run(comando, check=True, timeout=60)
    subprocess.run([binario], check=True, timeout=10)
