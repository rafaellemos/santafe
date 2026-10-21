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
    "provedores-sls.js",
    "realce-embutido.js",
    "realce-vscode.js",
    "aparencia.js",
    "paletas.json",
    "vendor/README.md",
    "vendor/vscode-textmate/package.json",
    "vendor/vscode-textmate/LICENSE.md",
    "vendor/vscode-textmate/release/main.js",
    "vendor/vscode-oniguruma/package.json",
    "vendor/vscode-oniguruma/LICENSE.txt",
    "vendor/vscode-oniguruma/NOTICES.txt",
    "vendor/vscode-oniguruma/release/main.js",
    "vendor/vscode-oniguruma/release/onig.wasm",
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
        def grave(nome, dados):
            info = zipfile.ZipInfo(nome, date_time=(2026, 10, 18, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            pacote.writestr(info, dados)

        grave(
            "[Content_Types].xml",
            """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">
  <Default Extension=\"json\" ContentType=\"application/json\" />
  <Default Extension=\"js\" ContentType=\"application/javascript\" />
  <Default Extension=\"md\" ContentType=\"text/markdown\" />
  <Default Extension=\"png\" ContentType=\"image/png\" />
  <Default Extension=\"wasm\" ContentType=\"application/wasm\" />
  <Default Extension=\"txt\" ContentType=\"text/plain\" />
  <Default Extension=\"xml\" ContentType=\"application/xml\" />
  <Default Extension=\"vsixmanifest\" ContentType=\"text/xml\" />
</Types>
""",
        )
        grave("extension.vsixmanifest", manifesto_vsix())
        for relativo in ARQUIVOS:
            grave(f"extension/{relativo}", (RAIZ / relativo).read_bytes())
    print(SAÍDA)


if __name__ == "__main__":
    principal()
