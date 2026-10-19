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
        assert arquivo.testzip() is None
        assert all(info.date_time == (2026, 10, 18, 0, 0, 0) for info in arquivo.infolist())
    primeira = vsix.read_bytes()
    subprocess.run([sys.executable, str(RAIZ / "empacotar.py")], check=True)
    assert vsix.read_bytes() == primeira, "VSIX precisa ser reproduzível byte a byte"
    esperados = {
        "extension/package.json",
        "extension/extension.js",
        "extension/realce-embutido.js",
        "extension/realce-vscode.js",
        "extension/aparencia.js",
        "extension/paletas.json",
        "extension/vendor/README.md",
        "extension/vendor/vscode-textmate/LICENSE.md",
        "extension/vendor/vscode-oniguruma/LICENSE.txt",
        "extension/vendor/vscode-oniguruma/NOTICES.txt",
        "extension/vendor/vscode-oniguruma/release/onig.wasm",
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
