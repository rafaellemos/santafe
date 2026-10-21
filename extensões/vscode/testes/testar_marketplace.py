#!/usr/bin/env python3
"""O pacote da galeria só acrescenta metadados, nunca altera o runtime."""

import argparse
import json
import pathlib
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from empacotar import ARQUIVOS
from preparar_marketplace import prepare


def confira_vsix(caminho):
    original = json.loads((RAIZ / "package.json").read_text(encoding="utf-8"))
    with zipfile.ZipFile(caminho) as pacote:
        assert pacote.testzip() is None
        nomes = set(pacote.namelist())
        esperados = {"extension/" + n for n in ARQUIVOS}
        esperados.remove("extension/README.md")
        esperados |= {"extension/readme.md", "extension/LICENSE.txt",
                      "extension.vsixmanifest", "[Content_Types].xml"}
        assert nomes == esperados, nomes ^ esperados
        for relativo in set(ARQUIVOS) - {"package.json", "README.md"}:
            assert pacote.read("extension/" + relativo) == (RAIZ / relativo).read_bytes(), relativo
        assert pacote.read("extension/LICENSE.txt") == (RAIZ.parents[1] / "LICENSE").read_bytes()
        manifesto = json.loads(pacote.read("extension/package.json"))
        leia_me = pacote.read("extension/readme.md").decode("utf-8")
        assert f"Extensão Santafé {manifesto['version']}" in leia_me
        assert "O SLS 1.0.0, publicado com o núcleo Santafé 2.1.0" in leia_me
        assert "análise semântica futura do SLS" not in leia_me
        for chave, valor in original.items():
            assert manifesto[chave] == valor, chave
        ns = {"v": "http://schemas.microsoft.com/developer/vsx-schema/2011"}
        xml = ET.fromstring(pacote.read("extension.vsixmanifest"))
        identidade = xml.find("v:Metadata/v:Identity", ns)
        assert identidade.get("Publisher") == original["publisher"]
        assert identidade.get("Id") == original["name"]
        assert identidade.get("Version") == original["version"]
        propriedades = {p.get("Id"): p.get("Value") for p in
                        xml.findall("v:Metadata/v:Properties/v:Property", ns)}
        assert propriedades["Microsoft.VisualStudio.Code.Engine"] == original["engines"]["vscode"]
        assert propriedades["Microsoft.VisualStudio.Services.Content.Pricing"] == "Free"
        ativos = {a.get("Type"): a.get("Path") for a in xml.findall("v:Assets/v:Asset", ns)}
        for tipo in ("Microsoft.VisualStudio.Code.Manifest",
                     "Microsoft.VisualStudio.Services.Content.Details",
                     "Microsoft.VisualStudio.Services.Content.License",
                     "Microsoft.VisualStudio.Services.Icons.Default"):
            assert ativos[tipo] in nomes
    print("VS Code Marketplace: VSIX oficial, identidade, arquivos e metadados: ok")


def principal():
    argumentos = argparse.ArgumentParser(description=__doc__)
    argumentos.add_argument("--vsix", type=pathlib.Path)
    opções = argumentos.parse_args()
    with tempfile.TemporaryDirectory(prefix="santafe-marketplace-teste-") as pasta:
        destino = pathlib.Path(pasta) / "extensão"
        prepare(destino)
        arquivos = {str(p.relative_to(destino)) for p in destino.rglob("*") if p.is_file()}
        assert arquivos == set(ARQUIVOS) | {"LICENSE.txt"}
        for relativo in set(ARQUIVOS) - {"package.json"}:
            assert (destino / relativo).read_bytes() == (RAIZ / relativo).read_bytes(), relativo
        assert (destino / "LICENSE.txt").read_bytes() == (RAIZ.parents[1] / "LICENSE").read_bytes()
        original = json.loads((RAIZ / "package.json").read_text(encoding="utf-8"))
        publicado = json.loads((destino / "package.json").read_text(encoding="utf-8"))
        assert publicado["files"] == list(ARQUIVOS) + ["LICENSE.txt"]
        for chave in ("homepage", "repository", "bugs", "files"):
            assert chave in publicado
            del publicado[chave]
        assert publicado == original, "a identidade e a configuração precisam ser preservadas"
        try:
            prepare(destino)
        except FileExistsError:
            pass
        else:
            raise AssertionError("não pode reaproveitar uma pasta existente")
    print("VS Code Marketplace: exportação mínima, licença e runtime preservado: ok")
    if opções.vsix:
        confira_vsix(opções.vsix)


if __name__ == "__main__":
    principal()
