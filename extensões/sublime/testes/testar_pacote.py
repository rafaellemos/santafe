#!/usr/bin/env python3
"""Valida a estrutura do pacote Santafé para Sublime Text."""

from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys
import zipfile


RAIZ = pathlib.Path(__file__).resolve().parents[1]


def principal() -> None:
    metadados = json.loads((RAIZ / "package-metadata.json").read_text(encoding="utf-8"))
    assert metadados["name"] == "Santafe"
    assert metadados["version"] == "1.0.13"
    assert (RAIZ / ".python-version").read_text(encoding="ascii").strip() == "3.8"
    sintaxe = (RAIZ / "Santafe.sublime-syntax").read_text(encoding="utf-8")
    assert "scope: source.santafe" in sintaxe
    assert "file_extensions:" in sintaxe and "- fé" in sintaxe
    assert "entity.name.function.santafe" in sintaxe
    assert "ident_before" in sintaxe
    contextos = re.findall(r"^  (\S[^\n:]*):$", sintaxe, re.MULTILINE)
    assert len(contextos) == len(set(contextos)), "contextos de sintaxe duplicados"
    assert "variable.parameter.santafe" in sintaxe
    assert "embed: scope:text.html.basic" in sintaxe
    assert "embed: scope:source.js" in sintaxe
    assert "palavra_reservada: '{{ident_before}}" in sintaxe
    assert '"selector": "source.santafe"' in (RAIZ / "Santafe.sublime-build").read_text(encoding="utf-8")
    subprocess.run([sys.executable, str(RAIZ / "gerar_catalogo.py")], check=True)
    subprocess.run([sys.executable, str(RAIZ / "testes" / "testar_comportamento.py")], check=True)
    subprocess.run([sys.executable, str(RAIZ / "testes" / "testar_recorte.py")], check=True)
    subprocess.run([sys.executable, str(RAIZ / "empacotar.py")], check=True)
    subprocess.run([sys.executable, str(RAIZ / "gerar_repositorio.py")], check=True)
    pacote = RAIZ / "dist" / "Santafe.sublime-package"
    with zipfile.ZipFile(pacote) as arquivo:
        assert arquivo.testzip() is None
        nomes = set(arquivo.namelist())
    esperados = {
        ".python-version", "Indentation Rules.tmPreferences", "Santafe.py", "Santafe.sublime-syntax", "Santafe.sublime-build", "Santafe.sublime-commands", "Default.sublime-keymap",
        "Santafe.sublime-settings", "api-publica.json", "package-metadata.json",
        "HTML-Santafe.sublime-syntax", "JavaScript-Santafe.sublime-syntax",
        "Realce.py", "realce_embutido.py",
        "snippets/funcao.sublime-snippet", "snippets/se.sublime-snippet",
    }
    assert esperados <= nomes, esperados - nomes
    with zipfile.ZipFile(pacote) as arquivo:
        for tema in ("Monokai", "Mariana", "Celeste", "Breakers", "Sixteen"):
            regras = json.loads(arquivo.read(f"ColorSchemes/{tema}.sublime-color-scheme"))["rules"]
            assert regras[0] == {"scope": "meta.santafe-embedded", "background": "#00000001"}
            assert len([r for r in regras if r['scope'].startswith('meta.santafe-soft-')]) == 36
            assert any(r.get('foreground') == '#FD971F' and r.get('font_style') == '' for r in regras)
    controle = RAIZ / "dist" / f"Santafe-{metadados['version']}.sublime-package"
    with zipfile.ZipFile(controle) as arquivo:
        assert arquivo.testzip() is None
        nomes = set(arquivo.namelist())
    assert "package-metadata.json" not in nomes
    assert ".python-version" in nomes
    assert "Indentation Rules.tmPreferences" in nomes
    assert all(arquivo.isascii() for arquivo in nomes)
    catálogo = json.loads((RAIZ / "dist" / "packages.json").read_text(encoding="utf-8"))
    assert catálogo["schema_version"] == "4.0.0"
    lançamento = catálogo["packages"][0]["releases"][0]
    assert catálogo["packages"][0]["name"] == "Santafe"
    assert lançamento["version"] == metadados["version"]
    assert lançamento["url"].endswith(f"/Santafe-{metadados['version']}.sublime-package")
    assert lançamento["url"].isascii()
    assert lançamento["python_versions"] == ["3.8", "3.14"]
    exportação = RAIZ / "dist" / "github"
    assert (exportação / "Santafe.py").is_file()
    assert not (exportação / "package-metadata.json").exists()
    assert not (exportação / "package-control-entrada.json").exists()
    assert (RAIZ / "dist" / "package-control-entrada.json").is_file()
    json.loads((RAIZ / "dist" / "package-control-entrada.json").read_text())
    assert (exportação / "README.md").read_text() == (RAIZ / "README.md").read_text()
    print("Pacote Sublime Santafé: estrutura e arquivo instalável: ok")


if __name__ == "__main__":
    principal()
