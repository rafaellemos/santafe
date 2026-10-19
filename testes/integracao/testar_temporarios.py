#!/usr/bin/env python3
"""Exercita as fixtures simultaneamente, sem tocar nos temporários históricos."""
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
TESTS = ("teste_imagem.fé", "teste_rpdf_imagens.fé", "teste_rpdf_minimo.fé",
         "teste_rpdf_unicode.fé", "teste_pulso.fé", "teste_temporarios.fé")
environment = dict(os.environ, LUA_PATH="bibs/bibf/?.fé;;", LUA_CPATH="bibs/bibc/?/?.so;;")


def run(name):
    source = ROOT / "testes/bibf" / name
    if name != "teste_temporarios.fé":  # este contém caminhos deliberadamente recusados
        assert '"/tmp/' not in source.read_text(), "fixture global voltou: " + name
    result = subprocess.run([str(ROOT / "src/santafé"), str(source)], cwd=ROOT,
                            env=environment, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, name + "\n" + result.stdout + result.stderr


with ThreadPoolExecutor(max_workers=4) as workers:
    list(workers.map(run, TESTS * 3))
print("Temporários: 18 execuções concorrentes sem colisão; limpeza inclusive após falha: ok")
