#!/usr/bin/env python3
"""Confere a suíte HTTP em fusos distintos, sem banco ou mensagens reais."""
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]

# Sequencial: cada execução abre o servidor de teste na mesma porta local.
for zone in ("UTC", "America/Sao_Paulo", "Asia/Tokyo"):
    environment = dict(os.environ, TZ=zone, GSETTINGS_BACKEND="memory",
                       LUA_PATH="bibs/bibf/?.fé;bibs/bibf/?.fe;;",
                       LUA_CPATH="bibs/bibc/?/?.so;;")
    result = subprocess.run(
        [str(ROOT / "src/santafé"), "testes/bibc/teste_carteiro_http.fé"],
        cwd=ROOT, env=environment, capture_output=True, text=True, timeout=60,
    )
    if result.returncode:
        raise AssertionError(f"Carteiro em {zone}:\n{result.stdout}{result.stderr}")
    print(f"Carteiro HTTP no fuso {zone}: ok")
