"""Recorte estático de colares concatenados; não executa Santafé nem imports.

Equivalente ao recortador do VS Code, em índices Unicode do Sublime (não UTF-16).
Os buracos representam expressões desconhecidas, nunca seu valor em execução.
"""
import re
import unicodedata

LONGO = re.compile(r"\[(=*)\[")
NUMERO = re.compile(r"(?:0[xX][\da-fA-F]+|\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)")
OPERADOR = re.compile(r"(?:\.\.\.|\.\.|==|~=|<=|>=|<<|>>|//)")
RESERVADAS = set("local função fim retorne se então senão para em início enquanto repita até pare vápara".split())
PRECEDENCIA = {"ou": 1, "e": 2, "<": 3, ">": 3, "<=": 3, ">=": 3, "~=": 3, "==": 3,
              "|": 4, "~": 5, "&": 6, "<<": 7, ">>": 7, "..": 8, "+": 9, "-": 9,
              "*": 10, "/": 10, "//": 10, "%": 10, "^": 12}
ESCAPES = dict(a="\a", b="\b", f="\f", n="\n", r="\r", t="\t", v="\v")


def fim_identificador(fonte, inicio):
    """[L_][LMN_]*, em pontos de código; preserva a forma NFC/NFD do nome."""
    if inicio >= len(fonte) or not (fonte[inicio] == "_" or
                                    unicodedata.category(fonte[inicio]).startswith("L")):
        return inicio
    fim = inicio + 1
    while fim < len(fonte) and (fonte[fim] == "_" or
                               unicodedata.category(fonte[fim])[0] in "LMN"):
        fim += 1
    return fim


def recorte(fonte):
    literais, fluxos = [], []
    i, total = 0, len(fonte)

    def comentario():
        nonlocal i
        inicio = i
        i += 2
        abre = LONGO.match(fonte, i)
        if abre:
            i = abre.end()
            fecha = "]" + abre[1] + "]"
            fim = fonte.find(fecha, i)
            i = total if fim < 0 else fim + len(fecha)
        else:
            fim = fonte.find("\n", i)
            i = total if fim < 0 else fim
        return fonte[inicio:i]

    def literal(anotacao, profundidade):
        nonlocal i
        inicio, marca, abre = i, fonte[i], LONGO.match(fonte, i)
        fecha = "]" + abre[1] + "]" if abre else marca
        i = abre.end() if abre else i + 1
        conteudo, trecho, partes = i, i, []
        while i < total and not fonte.startswith(fecha, i):
            if not abre and fonte[i] == "\\":
                i += 1
                if fonte[i:i+1] == "z":
                    i += 1
                    while i < total and fonte[i].isspace():
                        i += 1
                elif fonte[i:i+2] == "\r\n":
                    i += 2
                else:
                    i = min(total, i + 1)
            elif marca == "`" and fonte[i] in "®Ⓡ":
                fim_variavel = fim_identificador(fonte, i + 1)
                if fonte[i+1:i+2] == "{" and profundidade < 64:
                    if i > trecho:
                        partes.append(dict(inicio=trecho, fim=i))
                    buraco = i
                    i += 2
                    codigo(True, profundidade + 1)
                    partes.append(dict(inicio=buraco, fim=i, buraco=True))
                    trecho = i
                elif fim_variavel > i + 1:
                    if i > trecho:
                        partes.append(dict(inicio=trecho, fim=i))
                    buraco = i
                    i = fim_variavel
                    partes.append(dict(inicio=buraco, fim=i, buraco=True))
                    trecho = i
                else:
                    i += 1
            else:
                i += 1
        if i > trecho:
            partes.append(dict(inicio=trecho, fim=i))
        fechamento = i
        if fonte.startswith(fecha, i):
            i += len(fecha)
        valor = dict(tipo="literal", inicio=inicio, fim=i, conteudo=conteudo,
                     fechamento=fechamento, longo=bool(abre), anotacao=anotacao, partes=partes)
        literais.append(valor)
        return valor

    def codigo(expressao=False, profundidade=0):
        nonlocal i
        tokens, chaves, anotacao = [], 0, None
        fluxos.append(tokens)
        while i < total:
            if fonte[i].isspace():
                i += 1
                continue
            if fonte.startswith("--", i):
                anotado = re.fullmatch(r"--\[\[(html|javascript)\]\]", comentario())
                anotacao = anotado[1] if anotado else None
                continue
            if expressao and fonte[i] == "}" and chaves == 0:
                i += 1
                break
            chaves += (fonte[i] == "{") - (fonte[i] == "}")
            if fonte[i] in "\"'`" or LONGO.match(fonte, i):
                tokens.append(literal(anotacao, profundidade))
                anotacao = None
                continue
            anotacao, inicio = None, i
            fim_nome = fim_identificador(fonte, i)
            if fim_nome > i:
                i = fim_nome
                tipo = "nome"
            else:
                numero = NUMERO.match(fonte, i)
                sinal = OPERADOR.match(fonte, i) if not numero else None
                i = numero.end() if numero else sinal.end() if sinal else i + 1
                tipo = "numero" if numero else "sinal"
            tokens.append(dict(tipo=tipo, valor=fonte[inicio:i], inicio=inicio, fim=i))
    codigo()
    return literais, fluxos


def concatenacoes(tokens):
    i, grupos = 0, []
    def valor():
        return tokens[i].get("valor") if i < len(tokens) else None

    def atom(profundidade):
        nonlocal i
        if i >= len(tokens) or profundidade > 64 or valor() in RESERVADAS:
            return None
        t = tokens[i]
        if valor() in ("-", "#", "~", "não"):
            i += 1
            operando = expr(11, profundidade + 1)
            return dict(tipo="buraco", inicio=t["inicio"], fim=operando["fim"]) if operando else None
        if valor() == "(":
            i += 1
            no = expr(0, profundidade + 1)
            if valor() != ")" or no is None:
                return None
            no = dict(no, inicio=t["inicio"], fim=tokens[i]["fim"])
            i += 1
        elif valor() == "{":
            i += 1
            while i < len(tokens) and valor() != "}":
                antes = i
                expr(0, profundidade + 1)
                if antes == i:
                    i += 1
            if valor() != "}":
                return None
            no = dict(tipo="buraco", inicio=t["inicio"], fim=tokens[i]["fim"])
            i += 1
        elif t["tipo"] in ("literal", "nome", "numero"):
            i += 1
            no = dict(tipo="literal", literal=t, inicio=t["inicio"], fim=t["fim"]) if t["tipo"] == "literal" else dict(t, tipo="buraco")
        else:
            return None
        while i < len(tokens):
            if valor() in (".", ":") and i+1 < len(tokens) and tokens[i+1]["tipo"] == "nome":
                i += 2
                no = dict(tipo="buraco", inicio=no["inicio"], fim=tokens[i-1]["fim"])
            elif valor() in ("(", "["):
                fecha = ")" if valor() == "(" else "]"
                i += 1
                while i < len(tokens) and valor() != fecha:
                    antes = i
                    expr(0, profundidade + 1)
                    if i == antes:
                        i += 1
                if valor() != fecha:
                    return no
                no = dict(tipo="buraco", inicio=no["inicio"], fim=tokens[i]["fim"])
                i += 1
            else:
                break
        return no

    def primeiro(no):
        return no.get("literal") if no["tipo"] == "literal" else no.get("primeiro") if no["tipo"] == "concat" else None

    def expr(minimo=0, profundidade=0):
        nonlocal i
        esquerda = atom(profundidade)
        if esquerda is None:
            return None
        while i < len(tokens):
            op = valor()
            prioridade = PRECEDENCIA.get(op, -1)
            if prioridade < minimo or profundidade > 64:
                break
            i += 1
            direita = expr(prioridade + (0 if op == "^" else 1), profundidade + 1)
            if direita is None:
                break
            esquerda = dict(tipo="concat" if op == ".." else "buraco", inicio=esquerda["inicio"],
                            fim=direita["fim"], esquerda=esquerda, direita=direita,
                            primeiro=(primeiro(esquerda) or primeiro(direita)) if op == ".." else None)
            if op == "..":
                grupos.append(esquerda)
        return esquerda
    while i < len(tokens):
        antes = i
        expr()
        if i == antes:
            i += 1
    return grupos


def materialize(fonte, partes):
    texto, mapa = [], []
    def adicione(valor, inicio=-1, fim=-1):
        texto.append(valor)
        mapa.extend([(inicio, fim)] * len(valor))
    for literal in partes:
        if literal.get("buraco"):
            adicione("SANTAFE_HOLE")
            continue
        for parte in literal["partes"]:
            if parte.get("buraco"):
                adicione("SANTAFE_HOLE")
                continue
            p = parte["inicio"]
            while p < parte["fim"]:
                inicio = p
                if not literal["longo"] and fonte[p] == "\\":
                    p += 1
                    c = fonte[p:p+1]
                    p += bool(c)
                    if c == "z":
                        while p < parte["fim"] and fonte[p].isspace():
                            p += 1
                        continue
                    resto = fonte[p:parte["fim"]]
                    hexadecimal = re.match(r"[\da-fA-F]{2}", resto) if c == "x" else None
                    unicode = re.match(r"\{([\da-fA-F]{1,8})\}", resto) if c == "u" else None
                    if hexadecimal:
                        p += 2
                        adicione(chr(int(hexadecimal[0], 16)), inicio, p)
                    elif unicode and int(unicode[1], 16) <= 0x10ffff:
                        p += len(unicode[0])
                        adicione(chr(int(unicode[1], 16)), inicio, p)
                    elif c and c.isascii() and c.isdigit():
                        decimal = re.match(r"\d{1,3}", fonte[p-1:parte["fim"]])[0]
                        p += len(decimal)-1
                        adicione(chr(int(decimal) % 256), inicio, p)
                    else:
                        if c == "\r" and fonte[p:p+1] == "\n":
                            p += 1
                        adicione(ESCAPES.get(c, "\n" if c == "\r" else c), inicio, p)
                else:
                    p += 1
                    adicione(fonte[inicio], inicio, p)
    return dict(texto="".join(texto), mapa=mapa)


def documentos_embutidos(fonte):
    literais, fluxos = recorte(fonte)
    usados, visitados, linguagens, documentos = set(), set(), {}, []
    def linguagem(primeiro):
        if primeiro is None:
            return None
        chave = id(primeiro)
        if chave not in linguagens:
            texto = materialize(fonte, [primeiro])["texto"]
            linguagens[chave] = primeiro["anotacao"] or (
                "html" if re.search(r"<(?:!doctype\b|!--|/?[a-z][a-z0-9:-]*(?:\s|/?>))", texto.split("\n", 1)[0], re.I)
                else "javascript" if re.match(r"\s*/\*\s*(?:js|javascript)\s*\*/", texto) else None)
        return linguagens[chave]
    def considere(partes):
        reais = [p for p in partes if not p.get("buraco")]
        if not reais or any(id(p) in usados for p in reais):
            return
        idioma = linguagem(reais[0])
        if idioma:
            usados.update(id(p) for p in reais)
            documentos.append(dict(materialize(fonte, partes), linguagem=idioma))
    grupos = [g for fluxo in fluxos for g in concatenacoes(fluxo)]
    for grupo in sorted(grupos, key=lambda g: g["fim"]-g["inicio"], reverse=True):
        if id(grupo) in visitados or not linguagem(grupo["primeiro"]):
            continue
        partes, pilha = [], [grupo]
        while pilha:
            no = pilha.pop()
            if no["tipo"] == "concat":
                visitados.add(id(no))
                pilha.extend([no["direita"], no["esquerda"]])
            else:
                partes.append(no["literal"] if no["tipo"] == "literal" else dict(buraco=True))
        considere(partes)
    for literal in literais:
        considere([literal])
    return documentos
