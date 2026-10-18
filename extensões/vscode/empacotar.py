#!/usr/bin/env python3
"""Gera um VSIX determinístico da extensão Santafé sem exigir Node.js."""

from __future__ import annotations

import json
import pathlib
import zipfile


RAIZ = pathlib.Path(__file__).resolve().parent
MANIFESTO = json.loads((RAIZ / "package.json").read_text(encoding="utf-8"))
SAÍDA = RAIZ / "dist" / f"{MANIFESTO['name']}-{MANIFESTO['version']}.vsix"
ARQUIVOS = (
    "package.json",
    "extension.js",
    "api-publica.json",
    "icon.png",
    "language-configuration.json",
    "README.md",
    "syntaxes/santafe.tmLanguage.json",
    "snippets/santafe.code-snippets",
)


def manifesto_vsix() -> str:
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011">
  <Metadata>
    <Identity Id="{MANIFESTO['name']}" Version="{MANIFESTO['version']}" Publisher="{MANIFESTO['publisher']}" Language="pt-BR" />
    <DisplayName>{MANIFESTO['displayName']}</DisplayName>
    <Description xml:space="preserve">{MANIFESTO['description']}</Description>
  </Metadata>
  <Installation>
    <InstallationTarget Id="Microsoft.VisualStudio.Code" />
  </Installation>
  <Dependencies />
  <Assets>
    <Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" Addressable="true" />
  </Assets>
</PackageManifest>
'''


def principal() -> None:
    for relativo in ARQUIVOS:
        assert (RAIZ / relativo).is_file(), f"arquivo ausente: {relativo}"
    SAÍDA.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(SAÍDA, "w", compression=zipfile.ZIP_DEFLATED) as pacote:
        pacote.writestr(
            "[Content_Types].xml",
            """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">
  <Default Extension=\"json\" ContentType=\"application/json\" />
  <Default Extension=\"js\" ContentType=\"application/javascript\" />
  <Default Extension=\"md\" ContentType=\"text/markdown\" />
  <Default Extension=\"png\" ContentType=\"image/png\" />
  <Default Extension=\"xml\" ContentType=\"application/xml\" />
  <Default Extension=\"vsixmanifest\" ContentType=\"text/xml\" />
</Types>
""",
        )
        pacote.writestr("extension.vsixmanifest", manifesto_vsix())
        for relativo in ARQUIVOS:
            pacote.write(RAIZ / relativo, f"extension/{relativo}")
    print(SAÍDA)


if __name__ == "__main__":
    principal()
