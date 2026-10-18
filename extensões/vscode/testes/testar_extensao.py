#!/usr/bin/env python3
"""Validação estrutural da extensão VS Code Santafé."""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import zipfile


RAIZ = pathlib.Path(__file__).resolve().parents[1]
PACOTE = RAIZ / "package.json"


def principal() -> None:
    manifesto = json.loads(PACOTE.read_text(encoding="utf-8"))
    assert manifesto["main"] == "./extension.js"
    assert manifesto["icon"] == "./icon.png"
    assert manifesto["engines"]["vscode"].startswith("^")
    assert manifesto["extensionKind"] == ["workspace"]
    linguagem = manifesto["contributes"]["languages"][0]
    assert linguagem["id"] == "santafe"
    assert ".fé" in linguagem["extensions"]
    assert "santafe.languageServer.command" in manifesto["contributes"]["configuration"]["properties"]
    assert (RAIZ / "syntaxes/santafe.tmLanguage.json").is_file()
    assert (RAIZ / "snippets/santafe.code-snippets").is_file()
    assert (RAIZ / "api-publica.json").is_file()
    assert (RAIZ / "icon.png").is_file()
    cliente = (RAIZ / "extension.js").read_text(encoding="utf-8")
    assert "execuçãoDoSls" in cliente
    assert "ferramentas\", \"sls\", \"sls.fé" in cliente
    assert "registerCompletionItemProvider" in cliente
    assert "registerHoverProvider" in cliente
    assert "registerDocumentSymbolProvider" in cliente
    assert "registerDefinitionProvider" in cliente

    subprocess.run([sys.executable, str(RAIZ / "empacotar.py")], check=True)
    vsix = RAIZ / "dist" / f"{manifesto['name']}-{manifesto['version']}.vsix"
    with zipfile.ZipFile(vsix) as arquivo:
        nomes = set(arquivo.namelist())
    esperados = {
        "extension/package.json",
        "extension/extension.js",
        "extension/api-publica.json",
        "extension/icon.png",
        "extension/syntaxes/santafe.tmLanguage.json",
        "extension/snippets/santafe.code-snippets",
        "extension.vsixmanifest",
        "[Content_Types].xml",
    }
    assert esperados <= nomes, esperados - nomes
    print("Extensão VS Code Santafé: estrutura e VSIX ok")


if __name__ == "__main__":
    principal()
