#!/usr/bin/env python3
"""Gera pacotes de sintaxe paralelos; não instala nem publica extensões."""
import json
import pathlib
import zipfile
import os

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(os.environ.get("SANTAFE_EDITORES_OUT", ROOT / "dist/candidato-dados-v1/editores"))
OUT.mkdir(parents=True, exist_ok=True)

grammar = json.loads((ROOT / "extensões/vscode/syntaxes/santafe.tmLanguage.json").read_text())
grammar["name"] = "Santafé Dados Experimental"
grammar["scopeName"] = "source.santafe.dados"
# Reutiliza as capturas de Unicode/API e mantém o dialeto independente.
grammar["patterns"] = [
    {"include": "#comentário-longo"}, {"include": "#comentário"},
    {"include": "#bruto"}, {"include": "#gabarito"},
    {"include": "#colar-simples"}, {"include": "#colar"},
    {"include": "#função"}, {"include": "#declaração-anônima"},
    {"include": "#número"}, {"include": "#palavra-reservada"},
    {"include": "#constante"}, {"include": "#função-da-biblioteca"},
    {"include": "#operador"},
    {"name": "punctuation.section.list.santafe", "match": r"[\[\]]"},
]
grammar["repository"]["bruto"] = {
    "name": "string.quoted.other.raw.santafe", "begin": r"\[(=+)\[", "end": r"\]\1\]"
}
# A expressão do gabarito é código, não colar; marcadores Unicode fazem parte dela.
grammar["repository"]["interpolação"] = {"patterns": [
    {"name": "meta.interpolation.santafe", "begin": "[®Ⓡ]\\{", "end": "\\}",
     "beginCaptures": {"0": {"name": "punctuation.section.interpolation.begin.santafe"}},
     "endCaptures": {"0": {"name": "punctuation.section.interpolation.end.santafe"}},
     "patterns": [{"include": "#expressão-gabarito"}]},
    {"name": "variable.other.interpolation.santafe", "match": r"[®Ⓡ][\p{L}_][\p{L}\p{M}\p{N}_]*"}
]}
grammar["repository"]["expressão-gabarito"] = {"patterns": [
    {"begin": "\\{", "end": "\\}", "patterns": [{"include": "#expressão-gabarito"}]},
    {"include": "$self"}
]}
grammar_text = json.dumps(grammar, ensure_ascii=False, indent=2) + "\n"
(OUT / "santafe-dados.tmLanguage.json").write_text(grammar_text)

onfe = {"name": "ONFÉ Experimental", "scopeName": "source.onfe", "patterns": [
    {"include": "#comentário-longo"}, {"include": "#comentário"},
    {"include": "#bruto"}, {"include": "#colar-simples"}, {"include": "#colar"},
    {"include": "#número"},
    {"name": "constant.language.onfe", "match": r"\b(?:nulo|verdadeiro|falso)\b"},
    {"name": "variable.other.key.onfe", "match": r"[\p{L}_][\p{L}\p{M}\p{N}_]*(?=\s*=)"},
    {"name": "punctuation.separator.onfe", "match": r"[{}\[\],=]"},
    {"name": "invalid.illegal.onfe", "match": r"[^\s]"},
], "repository": grammar["repository"]}
onfe_text = json.dumps(onfe, ensure_ascii=False, indent=2) + "\n"
(OUT / "onfe.tmLanguage.json").write_text(onfe_text)

sublime = r'''%YAML 1.2
---
name: Santafé Dados Experimental
scope: source.santafe.dados
version: 2
contexts:
  main:
    - match: '--\[(=*)\['
      scope: punctuation.definition.comment.begin.santafe
      push:
        - meta_scope: comment.block.santafe
        - match: '\]\1\]'
          pop: true
    - match: '--.*$'
      scope: comment.line.santafe
    - match: '\[(=+)\['
      push:
        - meta_scope: string.quoted.other.raw.santafe
        - match: '\]\1\]'
          pop: true
    - match: '`'
      push: gabarito
    - match: '"'
      push:
        - meta_scope: string.quoted.double.santafe
        - match: '\\.'
          scope: constant.character.escape.santafe
        - match: '"'
          pop: true
    - match: "'"
      push:
        - meta_scope: string.quoted.single.santafe
        - match: '\\.'
          scope: constant.character.escape.santafe
        - match: "'"
          pop: true
    - match: '(?<![\p{L}\p{M}\p{N}_])função(?![\p{L}\p{M}\p{N}_])'
      scope: storage.type.function.santafe
    - match: '(?<![\p{L}\p{M}\p{N}_])(?:local|retorne|se|então|senão|senãose|para|em|início|fim|enquanto|repita|até|pare|e|ou|não)(?![\p{L}\p{M}\p{N}_])'
      scope: keyword.control.santafe
    - match: '(?<![\p{L}\p{M}\p{N}_])(?:nulo|verdadeiro|falso)(?![\p{L}\p{M}\p{N}_])'
      scope: constant.language.santafe
    - match: '\b[0-9]+(?:\.[0-9]+)?\b'
      scope: constant.numeric.santafe
    - match: '[{}()\[\],;:]'
      scope: punctuation.separator.santafe
  gabarito:
    - meta_scope: string.quoted.other.gabarito.santafe
    - match: '\\.'
      scope: constant.character.escape.santafe
    - match: '`'
      pop: true
    - match: '[®Ⓡ]\{'
      scope: punctuation.section.interpolation.begin.santafe
      push: expressão
    - match: '[®Ⓡ][\p{L}_][\p{L}\p{M}\p{N}_]*'
      scope: variable.other.interpolation.santafe
  expressão:
    - clear_scopes: 1
    - meta_scope: meta.interpolation.santafe
    - match: '\}'
      scope: punctuation.section.interpolation.end.santafe
      pop: true
    - match: '\{'
      push: expressão
    - include: main
'''
(OUT / "Santafe-Dados.sublime-syntax").write_text(sublime)
with zipfile.ZipFile(OUT / "Santafe-Dados-Experimental.sublime-package", "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("Santafe-Dados.sublime-syntax", sublime)
    z.writestr("ONFE.tmLanguage", __import__("plistlib").dumps(onfe))

manifest = {
    "name": "santafe-dados-experimental", "publisher": "santafe", "version": "0.0.1",
    "displayName": "Santafé Dados Experimental", "engines": {"vscode": "^1.86.0"},
    "description": "Gramática do candidato isolado; não substitui Santafé estável nem o SLS.",
    "categories": ["Programming Languages"], "license": "MIT",
    "contributes": {
        "languages": [
            {"id": "santafe-dados", "aliases": ["Santafé Dados Experimental"], "extensions": []},
            {"id": "onfe-experimental", "aliases": ["ONFÉ Experimental"], "extensions": [".onfé"]}],
        "grammars": [
            {"language": "santafe-dados", "scopeName": "source.santafe.dados", "path": "./santafe-dados.tmLanguage.json"},
            {"language": "onfe-experimental", "scopeName": "source.onfe", "path": "./onfe.tmLanguage.json"}]
    }
}
vsix_manifest = '''<?xml version="1.0" encoding="utf-8"?>
<PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011">
<Metadata><Identity Language="pt-BR" Id="santafe-dados-experimental" Version="0.0.1" Publisher="santafe"/>
<DisplayName>Santafé Dados Experimental</DisplayName><Description xml:space="preserve">Candidato de laboratório</Description>
<Tags>Santafé</Tags><Categories>Programming Languages</Categories><GalleryFlags>Public</GalleryFlags>
<Properties><Property Id="Microsoft.VisualStudio.Code.Engine" Value="^1.86.0"/></Properties></Metadata>
<Installation><InstallationTarget Id="Microsoft.VisualStudio.Code"/></Installation><Dependencies/>
<Assets><Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" Addressable="true"/></Assets>
</PackageManifest>'''
with zipfile.ZipFile(OUT / "santafe-dados-experimental-0.0.1.vsix", "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("extension.vsixmanifest", vsix_manifest)
    z.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="json" ContentType="application/json"/><Default Extension="vsixmanifest" ContentType="text/xml"/></Types>')
    z.writestr("extension/package.json", json.dumps(manifest, ensure_ascii=False))
    z.writestr("extension/santafe-dados.tmLanguage.json", grammar_text)
    z.writestr("extension/onfe.tmLanguage.json", onfe_text)
print("EDITORES_EXPERIMENTAIS_GERADOS", OUT)
