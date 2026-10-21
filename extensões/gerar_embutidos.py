#!/usr/bin/env python3
"""Gera as regras equivalentes de colares/gabaritos dos dois editores.

O realce não altera a linguagem: HTML é identificado pela marcação na linha inicial;
JavaScript pelo comentário inicial /* javascript */ (ou /* js */).
Para conteúdo que começa na linha seguinte, use --[[html]] ou --[[javascript]]
antes do delimitador, na mesma linha. As gramáticas HTML/JS são as do editor.
"""
from pathlib import Path
import json

RAIZ = Path(__file__).resolve().parent
HTML = r"<(?:!(?i:DOCTYPE)\b|!--|/?[A-Za-z][A-Za-z0-9:-]*(?:\s|/?>))"
JS = r"[ \t]*(?=/\*\s*(?:javascript|js)\s*\*/)"
COLARES = [
    ("long", r"\[(=*)\[", r"\]\1\]"),
    ("gabarito", "`", "`"),
    ("double", '"', '"'),
    ("single", "'", "'"),
]


def detecte_html(fim):
    # Fragmentos concatenados também podem começar com texto: [[ | Site</title>]].
    # Nunca procure marcação após o delimitador do colar atual: isso confundiria
    # as aspas de escapeHTML com as de um HTML que aparece mais adiante.
    return rf"(?=(?:(?!{fim}).)*?{HTML})"


def textmate():
    caminho = RAIZ / "vscode/syntaxes/santafe.tmLanguage.json"
    gramática = json.loads(caminho.read_text())
    repo = gramática["repository"]
    repo["escape"] = {"name": "constant.character.escape.santafe", "match": r"\\."}
    repo["interpolação"] = {"patterns": [
        {"name": "meta.interpolation.santafe", "begin": r"[®Ⓡ]\{", "end": r"\}",
         "contentName": "meta.embedded.inline.santafe",
         "beginCaptures": {"0": {"name": "punctuation.section.interpolation.begin.santafe keyword.operator.interpolation.santafe"}},
         "endCaptures": {"0": {"name": "punctuation.section.interpolation.end.santafe keyword.operator.interpolation.santafe"}},
         "patterns": [{"include": "#chaves"}, {"include": "$self"}]},
        # O marcador integra o token da variável; pontuação sem estilo próprio
        # herdava a cor do colar em temas como Monokai e Dark+.
        {"match": r"[®Ⓡ][\p{L}_][\p{L}\p{M}\p{N}_]*",
         "name": "meta.interpolation.variable.santafe variable.parameter.santafe"},
    ]}
    repo["chaves"] = {"begin": r"\{", "end": r"\}",
                      "patterns": [{"include": "#chaves"}, {"include": "$self"}]}
    repo["gabarito"]["patterns"] = [{"include": "#escape"}, {"include": "#interpolação"}]
    # VS Code: primeiro delimitar Santafé. A camada realce-embutido.js tokeniza
    # documentos virtuais concatenados e colore somente seus trechos literais.
    # Incluir HTML/JS diretamente aqui esconderia o end do colar quando uma
    # concatenação corta atributos ou comentários nativos ao meio.
    repo.pop("embutidos", None)
    gramática["patterns"] = [p for p in gramática["patterns"] if p["include"] != "#embutidos"]
    gramática.pop("injections", None)
    caminho.write_text(json.dumps(gramática, ensure_ascii=False, indent=2) + "\n")


def yaml_quote(s):
    return "'" + s.replace("'", "''") + "'"


def sublime():
    caminho = RAIZ / "sublime/Santafe.sublime-syntax"
    texto = caminho.read_text()
    # As anotações precisam preceder comentários (inclusive no prototype).
    texto = texto.replace("  prototype:\n    - include: embutidos-anotados\n", "  prototype:\n")
    if "  código:\n" not in texto:
        texto = texto.replace("  main:\n    - include: embutidos\n", "  main:\n")
        texto = texto.replace("  main:\n", "  main:\n    - include: embutidos-anotados\n    - include: embutidos\n    - include: código\n\n  código:\n")
    # As anotações válidas são consumidas por main, sem incorporá-las em
    # prototype (isso recursaria ao embutir HTML/JS dentro da expressão).
    texto = texto.replace("    - match: '--\\[(=*)\\['", "    - match: '--(?!\\[\\[(?:html|javascript)\\]\\][ \\t]*(?:\\[=*\\[|[\"''`]))\\[(=*)\\['")
    texto = texto.replace("    - match: '--'", "    - match: '--(?!\\[\\[(?:html|javascript)\\]\\][ \\t]*(?:\\[=*\\[|[\"''`]))'")
    início = texto.index("  embutidos-anotados:\n") if "  embutidos-anotados:\n" in texto else texto.index("  gabaritos:\n")
    fim = texto.index("  números:\n", início)
    partes = []
    for anotado in (True, False):
        partes.append("  embutidos-anotados:" if anotado else "  embutidos:")
        for linguagem, detecção, gram in [("html", HTML, "text.html.basic"), ("javascript", JS, "source.js")]:
            for tipo, começo, término in COLARES:
                detecte = detecte_html(término) if linguagem == "html" else detecção
                regex = (rf"(--\[\[{linguagem}\]\])[ \t]*(?:{começo})" if anotado else começo + detecte)
                escape = término.replace(r"\1", r"\2") if anotado else término
                partes += [f"    - match: {yaml_quote(regex)}",
                           "      scope: punctuation.definition.string.begin.santafe"]
                if tipo != "gabarito":
                    if tipo != "long":
                        escape = r"(?<!\\)(?:\\\\)*" + escape
                    # embed fecha até contextos aninhados e preserva a quantidade de '='.
                    partes += [f"      embed: scope:{gram}",
                               f"      embed_scope: meta.embedded.block.{linguagem}.santafe",
                               f"      escape: {yaml_quote(escape)}",
                               "      escape_captures:",
                               "        0: punctuation.definition.string.end.santafe"]
                else:
                    escopo = "text.html" if linguagem == "html" else "source.js"
                    partes += [f"      embed: scope:{escopo}.santafe-template",
                               f"      embed_scope: meta.embedded.block.{linguagem}.santafe",
                               "      escape: '(?<!\\\\)(?:\\\\\\\\)*`'",
                               "      escape_captures:",
                               "        0: punctuation.definition.string.end.santafe"]
        partes.append("")
    partes.append(r'''  escape-colar:
    - match: '\\.'
      scope: constant.character.escape.santafe

  interpolação:
    - match: '[®Ⓡ]\{'
      scope: punctuation.section.interpolation.begin.santafe keyword.operator.interpolation.santafe
      push:
        - clear_scopes: true
        - meta_scope: meta.interpolation.santafe meta.embedded.inline.santafe source.santafe
        - meta_include_prototype: false
        - match: '\}'
          scope: punctuation.section.interpolation.end.santafe keyword.operator.interpolation.santafe
          pop: true
        - include: chaves-interpolação
        - include: código
    - match: '[®Ⓡ][\p{L}_][\p{L}\p{M}\p{N}_]*'
      scope: meta.interpolation.variable.santafe variable.parameter.santafe

  chaves-interpolação:
    - match: '\{'
      push:
        - meta_include_prototype: false
        - match: '\}'
          pop: true
        - include: chaves-interpolação
        - include: código

  gabaritos:
    - match: '`'
      scope: punctuation.definition.string.begin.santafe
      push:
        - meta_scope: string.quoted.other.gabarito.santafe
        - meta_include_prototype: false
        - match: '`'
          scope: punctuation.definition.string.end.santafe
          pop: true
        - include: escape-colar
        - include: interpolação

  colares:
    - match: '\[(=*)\['
      push:
        - meta_scope: string.quoted.other.long.santafe
        - meta_include_prototype: false
        - match: '\]\1\]'
          pop: true
    - match: "'"
      push:
        - meta_scope: string.quoted.single.santafe
        - meta_include_prototype: false
        - match: "'"
          pop: true
        - include: escape-colar
    - match: '"'
      push:
        - meta_scope: string.quoted.double.santafe
        - meta_include_prototype: false
        - match: '"'
          pop: true
        - include: escape-colar

''')
    caminho.write_text(texto[:início] + "\n".join(partes) + texto[fim:])


if __name__ == "__main__":
    textmate()
    sublime()
