#!/usr/bin/env python3
"""Rasteriza a marca oficial do portal; não redesenha nem inventa um ícone."""

import argparse
import hashlib
import pathlib
import subprocess

RAIZ = pathlib.Path(__file__).resolve().parent
SHA256_SVG = "9ce5cab0e3fb7eea923712240e05c68d0fdddad817ed75160220426d43ad82fa"


def principal():
    argumentos = argparse.ArgumentParser(description=__doc__)
    argumentos.add_argument("--node", default="node", help="executável Node.js")
    argumentos.add_argument("--sharp", default="sharp", help="módulo Sharp ou caminho absoluto")
    opções = argumentos.parse_args()
    fonte = RAIZ / "icon.svg"
    if hashlib.sha256(fonte.read_bytes()).hexdigest() != SHA256_SVG:
        raise SystemExit("SVG diferente da marca oficial registrada em MARCA.md")
    # O SVG fica versionado; não há acesso à rede nem redesenho da marca.
    # Sharp só é necessário para regenerar o PNG, nunca para usar a extensão.
    subprocess.run([opções.node, "-e", """
const sharp = require(process.argv[1]);
sharp(process.argv[2]).resize(256, 256)
  .png({compressionLevel: 9, adaptiveFiltering: false})
  .toFile(process.argv[3])
  .then(() => console.log('Marca oficial Santafé: PNG 256×256 gerado'))
  .catch(erro => { console.error(erro.message); process.exitCode = 1; });
""", opções.sharp, str(fonte), str(RAIZ / "icon.png")], check=True)


if __name__ == "__main__":
    principal()
