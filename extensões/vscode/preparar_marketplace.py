#!/usr/bin/env python3
"""Prepara uma árvore mínima para o vsce, sem substituir o VSIX do portal."""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil

from empacotar import ARQUIVOS, RAIZ


REPOSITÓRIO = "https://github.com/rafaellemos/santafe"


def prepare(destino: pathlib.Path) -> None:
    # Recusar uma pasta existente evita misturar fontes/segredos ou sobrescrever
    # arquivos do usuário. O vsce só verá a lista pública explícita do VSIX.
    destino.mkdir(parents=True, exist_ok=False)
    for relativo in ARQUIVOS:
        origem = RAIZ / relativo
        if origem.is_symlink() or not origem.is_file():
            raise ValueError(f"fonte público inválido: {relativo}")
        saída = destino / relativo
        saída.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(origem, saída)

    manifesto = json.loads((destino / "package.json").read_text(encoding="utf-8"))
    manifesto.update({
        "homepage": "https://xn--santaf-gva.dev.br/",
        "repository": {"type": "git", "url": REPOSITÓRIO + ".git",
                       "directory": "extensões/vscode"},
        "bugs": {"url": REPOSITÓRIO + "/issues"},
        "files": list(ARQUIVOS) + ["LICENSE.txt"],
    })
    (destino / "package.json").write_text(
        json.dumps(manifesto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    shutil.copyfile(RAIZ.parents[1] / "LICENSE", destino / "LICENSE.txt")


def principal() -> None:
    argumentos = argparse.ArgumentParser(description=__doc__)
    argumentos.add_argument("destino", type=pathlib.Path,
                            help="nova pasta temporária, ainda inexistente")
    opções = argumentos.parse_args()
    prepare(opções.destino)
    print(opções.destino.resolve())


if __name__ == "__main__":
    principal()
