#!/usr/bin/env python3
"""Gera o pacote instalável do Sublime Text de modo reproduzível."""

from __future__ import annotations

import json
import pathlib
import zipfile


RAIZ = pathlib.Path(__file__).resolve().parent
METADADOS = json.loads((RAIZ / "package-metadata.json").read_text(encoding="utf-8"))
# O nome do arquivo define o nome do pacote dentro do Sublime.  Mantê-lo
# canônico faz `Packages/Santafe/...` funcionar tanto para a instalação manual
# como para futuras atualizações do mesmo pacote.
SAÍDA_MANUAL = RAIZ / "dist" / "Santafe.sublime-package"
SAÍDA_CONTROLE = RAIZ / "dist" / f"Santafe-{METADADOS['version']}.sublime-package"
ARQUIVOS = (
    ".python-version",
    "Indentation Rules.tmPreferences",
    "Santafe.py",
    "Realce.py",
    "realce_embutido.py",
    "paletas.json",
    "ColorSchemes/Monokai.sublime-color-scheme",
    "ColorSchemes/Mariana.sublime-color-scheme",
    "ColorSchemes/Celeste.sublime-color-scheme",
    "ColorSchemes/Breakers.sublime-color-scheme",
    "ColorSchemes/Sixteen.sublime-color-scheme",
    "Santafe.sublime-build",
    "Santafe.sublime-commands",
    "Default.sublime-keymap",
    "Santafe.sublime-settings",
    "Santafe.sublime-syntax",
    "HTML-Santafe.sublime-syntax",
    "JavaScript-Santafe.sublime-syntax",
    "LSP-santafe.sublime-settings.example",
    "README.md",
    "api-publica.json",
    "package-metadata.json",
    "snippets/funcao.sublime-snippet",
    "snippets/se.sublime-snippet",
    "snippets/para.sublime-snippet",
    "snippets/mostre.sublime-snippet",
)


ARQUIVOS_DO_CONTROLE = tuple(
    arquivo for arquivo in ARQUIVOS if arquivo != "package-metadata.json"
)


def empacote(saída, arquivos) -> None:
    with zipfile.ZipFile(saída, "w", compression=zipfile.ZIP_DEFLATED) as pacote:
        for relativo in arquivos:
            arquivo = RAIZ / relativo
            informação = zipfile.ZipInfo(relativo, date_time=(2026, 10, 17, 0, 0, 0))
            informação.compress_type = zipfile.ZIP_DEFLATED
            informação.external_attr = 0o644 << 16
            pacote.writestr(informação, arquivo.read_bytes())


def principal() -> None:
    ausentes = [arquivo for arquivo in ARQUIVOS if not (RAIZ / arquivo).is_file()]
    if ausentes:
        raise SystemExit("arquivos ausentes: " + ", ".join(ausentes))
    SAÍDA_MANUAL.parent.mkdir(exist_ok=True)
    empacote(SAÍDA_MANUAL, ARQUIVOS)
    empacote(SAÍDA_CONTROLE, ARQUIVOS_DO_CONTROLE)
    print(SAÍDA_MANUAL)
    print(SAÍDA_CONTROLE)


if __name__ == "__main__":
    principal()
