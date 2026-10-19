#!/usr/bin/env python3
"""Empacota artefatos já testados, sem instalar, conectar ou reiniciar serviços."""
import argparse
import gzip
import hashlib
import io
from pathlib import Path
import tarfile

RAIZ = Path(__file__).resolve().parents[1]
FONTES = {
    "baixar/santafe-vscode-1.0.6.vsix": "extensões/vscode/dist/santafe-1.0.6.vsix",
    "baixar/Santafe.sublime-package": "extensões/sublime/dist/Santafe.sublime-package",
    "sublime/Santafe-1.0.13.sublime-package": "extensões/sublime/dist/Santafe-1.0.13.sublime-package",
    "sublime/packages.json": "extensões/sublime/dist/packages.json",
    "preparar-editores-portal.py": "operação/preparar-editores-portal.py",
}


def principal():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("saida", type=Path)
    args = parser.parse_args()
    itens = {destino: (RAIZ / fonte).read_bytes() for destino, fonte in FONTES.items()}
    itens["SHA256SUMS"] = "".join(f"{hashlib.sha256(dados).hexdigest()}  {nome}\n"
        for nome, dados in sorted(itens.items())).encode()
    # Nada de xattrs locais, donos de estação ou carimbos variáveis.
    with args.saida.open("xb") as arquivo, gzip.GzipFile(filename="", fileobj=arquivo, mode="wb", mtime=0) as gz:
        with tarfile.open(fileobj=gz, mode="w") as pacote:
            for nome, dados in sorted(itens.items()):
                info = tarfile.TarInfo(nome)
                info.size, info.mode, info.mtime = len(dados), 0o644, 0
                pacote.addfile(info, io.BytesIO(dados))
    print(hashlib.sha256(args.saida.read_bytes()).hexdigest(), args.saida)


if __name__ == "__main__":
    principal()
