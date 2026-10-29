#!/usr/bin/env python3
"""Gera o catálogo HTTPS e a exportação limpa do Sublime Package Control."""

from __future__ import annotations

import hashlib
import json
import pathlib
import shutil

from empacotar import ARQUIVOS_DO_CONTROLE, METADADOS, RAIZ, SAÍDA_CONTROLE


DOMINIO = "https://xn--santaf-gva.dev.br"
ESTATICO_PUBLICO = f"{DOMINIO}/est%C3%A1tico"
NOME = METADADOS["name"]
VERSAO = METADADOS["version"]
DIST = RAIZ / "dist"
CATALOGO = DIST / "packages.json"
ENTRADA_CONTROLE = DIST / "package-control-entrada.json"
GITHUB = DIST / "github"
# A 1.0.13 lê o catálogo da API ao importar o plugin. Essa operação é segura
# desde o build 4171. Declare o requisito no canal sem reescrever os arquivos
# 1.0.13 já publicados no portal nem alterar etiquetas anteriores.
SUBLIME_CATALOGO = ">=4171"
ARQUIVOS_DO_CATALOGO = ("Main.sublime-menu", "Default.sublime-commands")


def catálogo() -> dict:
    return {
        "$schema": "sublime://packagecontrol.io/schemas/repository",
        "schema_version": "4.0.0",
        "packages": [
            {
                "name": NOME,
                "description": (
                    "Suporte oficial à linguagem Santafé 3 e ONFÉ: sintaxe, trechos, "
                    "conclusões da API e integração opcional ao SLS."
                ),
                "author": "Rafael Alves Lemos",
                "homepage": f"{DOMINIO}/",
                "labels": ["language syntax", "snippets", "linting"],
                "releases": [
                    {
                        "version": VERSAO,
                        "url": f"{ESTATICO_PUBLICO}/sublime/{SAÍDA_CONTROLE.name}",
                        "date": "2026-10-29 00:00:00",
                        "sha256": hashlib.sha256(SAÍDA_CONTROLE.read_bytes()).hexdigest(),
                        "platforms": ["*"],
                        "sublime_text": METADADOS["sublime_text"],
                        # O arquivo .python-version no pacote evita um defeito
                        # do Package Control 4.2.8 ao avaliar esta lista em ST 4215.
                        "python_versions": ["3.8", "3.14"],
                    }
                ],
            }
        ],
    }


def escreva(destino: pathlib.Path, conteúdo: str) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(conteúdo, encoding="utf-8")


def exporte_github() -> None:
    if GITHUB.exists():
        shutil.rmtree(GITHUB)
    GITHUB.mkdir(parents=True)
    for relativo in ARQUIVOS_DO_CONTROLE:
        origem = RAIZ / relativo
        destino = GITHUB / relativo
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origem, destino)
    shutil.copy2(RAIZ / "CHANGELOG.md", GITHUB / "CHANGELOG.md")
    shutil.copy2(RAIZ.parents[1] / "LICENSE", GITHUB / "LICENSE")
    for nome in ARQUIVOS_DO_CATALOGO:
        shutil.copy2(RAIZ / "catalogo" / nome, GITHUB / nome)
    escreva(
        ENTRADA_CONTROLE,
        json.dumps(
            {
                "name": NOME,
                "details": "https://github.com/rafaellemos/santafe-sublime",
                "releases": [
                    {
                        "sublime_text": SUBLIME_CATALOGO,
                        # O canal central usa esquema 3.0.0 e não aceita
                        # python_versions. O pacote seleciona o host pelo
                        # arquivo .python-version, também exportado.
                        "tags": True,
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
    )


def principal() -> None:
    if not SAÍDA_CONTROLE.is_file():
        raise SystemExit(f"pacote ausente: {SAÍDA_CONTROLE}; execute empacotar.py antes")
    escreva(CATALOGO, json.dumps(catálogo(), ensure_ascii=False, indent=2) + "\n")
    exporte_github()
    print(CATALOGO)
    print(ENTRADA_CONTROLE)
    print(GITHUB)


if __name__ == "__main__":
    principal()
