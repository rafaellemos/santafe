"""Critérios executáveis para a evolução do SLS; nenhum teste é marcado xfail.

`atual` é o contrato já entregue. `1.0` acrescenta o contrato-alvo. Falta de
capacidade é PENDENTE; capacidade anunciada com comportamento errado é FALHA.
Não é uma alegação de cobertura exaustiva de LSP nem de todas as linguagens
embutidas. O restante da homologação está descrito em docs/SLS-1.0.md.
"""
from __future__ import annotations

import json
import time

from .cliente import FalhaLsp, Pendente, aplique_edicoes, deslocamento, edicoes_por_uri, posicao, recorte


CASOS = []


def caso(nome, grupo, perfil="1.0", capacidade=None):
    def registre(funcao):
        CASOS.append({"id": nome, "grupo": grupo, "perfil": perfil,
                      "capacidade": capacidade, "execute": funcao})
        return funcao
    return registre


def confira(condicao, motivo):
    if not condicao:
        raise FalhaLsp(motivo)


def conclusoes(resposta):
    itens = resposta.get("items") if isinstance(resposta, dict) else resposta
    confira(isinstance(itens, list), "completion precisa devolver itens")
    return {item["label"] for item in itens}


def localizacoes(resposta):
    itens = resposta if isinstance(resposta, list) else [resposta] if resposta else []
    return [(item.get("uri", item.get("targetUri")),
             item.get("range", item.get("targetSelectionRange"))) for item in itens]


def nomes_simbolos(itens):
    nomes = set()
    for item in itens or []:
        nomes.add(item["name"])
        nomes.update(nomes_simbolos(item.get("children", [])))
    return nomes


def texto_hover(resultado):
    confira(isinstance(resultado, dict) and resultado.get("contents"), "hover vazio")
    return json.dumps(resultado["contents"], ensure_ascii=False)


@caso("identidade-e-sincronizacao", "protocolo", "atual")
def identidade(c, contexto):
    confira(c.informacao.get("name") == "SLS", "serverInfo.name diferente de SLS")
    confira(bool(c.informacao.get("version")), "versão do SLS ausente")
    confira(c.capacidades.get("positionEncoding", "utf-16") == "utf-16", "codificação não negociada")
    sync = c.capacidades.get("textDocumentSync", {})
    confira(isinstance(sync, dict) and sync.get("openClose") and sync.get("change") in (1, 2),
            "sincronização de documentos não anunciada")


@caso("erro-e-correcao", "diagnosticos", "atual")
def erro_correcao(c, contexto):
    uri = c.abra("se verdadeiro então\n")
    erros = c.diagnosticos(uri, 1)
    confira(erros and erros[0].get("severity") == 1, "erro sintático não publicado")
    confira(erros[0].get("source") == "SLS", "origem do diagnóstico incorreta")
    versao = c.mude(uri, "se verdadeiro então\n    mostre(42)\nfim\n")
    confira(c.diagnosticos(uri, versao) == [], "diagnóstico antigo permaneceu após correção")


@caso("salvar-fechar-reabrir", "documentos", "atual")
def salvar_fechar(c, contexto):
    texto = "local valor = 42\n"
    uri = c.abra(texto)
    confira(c.diagnosticos(uri, 1) == [], "documento válido recusado")
    c.notifique("textDocument/didSave", {"textDocument": {"uri": uri}, "text": texto})
    confira(c.diagnosticos(uri) == [], "salvamento gerou erro")
    c.notifique("textDocument/didClose", {"textDocument": {"uri": uri}})
    confira(c.diagnosticos(uri) == [], "fechamento não limpou diagnóstico")
    c.abra("local x = )\n")
    confira(bool(c.diagnosticos(uri, 1)), "reabertura usou documento antigo")


@caso("mesmo-nome-em-pastas-diferentes", "documentos", "atual")
def duas_pastas(c, contexto):
    primeiro = c.abra("local x = )", "um/exemplo.fé")
    segundo = c.abra("mostre(42)", "dois/exemplo.fé")
    confira(bool(c.diagnosticos(primeiro, 1)), "erro do primeiro arquivo desapareceu")
    confira(c.diagnosticos(segundo, 1) == [], "diagnósticos vazaram para outra URI")


@caso("versoes-antigas-nao-sobrescrevem", "documentos", "atual")
def versoes(c, contexto):
    uri = c.abra("local valor = 42")
    c.diagnosticos(uri, 1)
    c.mude(uri, "local valor = 43")
    c.diagnosticos(uri, 2)
    c.notifique("textDocument/didChange", {"textDocument": {"uri": uri, "version": 1},
                                        "contentChanges": [{"text": "local valor = )"}]})
    c.notifique("textDocument/didSave", {"textDocument": {"uri": uri}})
    confira(c.diagnosticos(uri) == [], "mudança fora de ordem contaminou o texto atual")


@caso("fonte-nunca-e-executado", "seguranca", "atual")
def nao_executar(c, contexto):
    uri = c.abra('local arquivo = es.abra("efeito-colateral.txt", "w")\n'
                 'arquivo:escreva("não executar")\nerro("não avaliar o fonte")\n')
    confira(c.diagnosticos(uri, 1) == [], "código válido foi executado ou recusado")
    confira(not (c.raiz / "efeito-colateral.txt").exists(), "SLS executou o documento")


@caso("importacao-nao-executa-modulo", "seguranca", "atual")
def nao_importar(c, contexto):
    uri = c.abra('local modulo = importe "nao_existe_modulo_de_teste"\n')
    erros = c.diagnosticos(uri, 1)
    # Um SLS semântico pode informar importação não resolvida, mas não lançar erro de runtime.
    confira(all(item.get("source") == "SLS" for item in erros), "importação executada")
    resposta = c.solicite_bruto("santafe/metodo-inexistente")
    confira(resposta.get("error", {}).get("code") == -32601, "servidor deixou de responder")


@caso("unicode-e-caminho-com-espacos", "unicode", "atual")
def unicode(c, contexto):
    uri = c.abra('local índice = "ação 🟢 é"\nmostre(índice)\n', "pasta com espaços/ação.fé")
    confira(c.diagnosticos(uri, 1) == [], "fonte/URI Unicode inválido")


@caso("gabaritos-e-html-js-nao-geram-erros", "unicode", "atual")
def gabaritos(c, contexto):
    texto = '''local nome = "José"
local html = --[[html]] [[<a title="]] .. nome .. [[">link</a>]]
local js = --[[javascript]] [[/* início ]] .. nome .. [[ fim */ const x = 1;]]
local gabarito = `®nome Ⓡnome ®{1 + 2} Ⓡ{1 + 2}`
'''
    if ("dados." in c.informacao.get("version", "") or c.informacao.get("version") == "1.1.0"):
        # Só os delimitadores dos colares mudam; comentários anotados permanecem.
        texto = texto.replace(' [[', ' [=[').replace(']] ..', ']=] ..').replace('>]]', '>]=]').replace(';]]', ';]=]')
    uri = c.abra(texto)
    confira(c.diagnosticos(uri, 1) == [], "gabaritos ou concatenações não compilam")


@caso("parametros-invalidos-nao-derrubam", "protocolo", "atual")
def parametros(c, contexto):
    resposta = c.solicite_bruto("teste/desconhecido", False)
    confira(resposta.get("error", {}).get("code") == -32602, "params inválidos aceitos")
    c.notifique("textDocument/didOpen", {"textDocument": False})
    uri = c.abra("mostre(1)")
    confira(c.diagnosticos(uri, 1) == [], "servidor parou após notificação inválida")


@caso("rajada-de-edicoes", "desempenho", "atual")
def rajada(c, contexto):
    uri = c.abra("local x = 0")
    c.diagnosticos(uri, 1)
    for indice in range(1, 31):
        versao = c.mude(uri, "local x = " + str(indice))
    confira(c.diagnosticos(uri, versao) == [], "última edição da rajada não analisada")


@caso("documento-de-1500-linhas", "desempenho", "atual")
def grande(c, contexto):
    # Escopo limitado: não esgotar o limite de variáveis locais do próprio compilador.
    texto = ("início local índice = 42 fim\n" * 1500)
    inicio = time.monotonic()
    uri = c.abra(texto)
    confira(c.diagnosticos(uri, 1) == [], "documento grande válido recusado")
    contexto["medidas"]["diagnostico_1500_linhas_ms"] = round((time.monotonic() - inicio) * 1000, 2)


@caso("intervalo-exato-apos-emoji", "diagnosticos")
def intervalo(c, contexto):
    texto = 'local emoji = "🟢"; local índice = )\n'
    uri = c.abra(texto)
    erros = c.diagnosticos(uri, 1)
    confira(bool(erros), "erro ausente")
    confira(any(recorte(texto, item["range"]) == ")" for item in erros),
            "diagnóstico deve selecionar o token incorreto em UTF-16, não a linha inteira/coluna zero")


@caso("edicao-incremental-utf16", "documentos")
def incremental(c, contexto):
    sync = c.capacidades.get("textDocumentSync", {})
    if not isinstance(sync, dict) or sync.get("change") != 2:
        raise Pendente("sincronização incremental ainda não anunciada")
    texto = 'local x = "🟢 é"; mostre(x)\r\n'
    uri = c.abra(texto)
    c.diagnosticos(uri, 1)
    indice = texto.index("mostre")
    c.notifique("textDocument/didChange", {"textDocument": {"uri": uri, "version": 2},
        "contentChanges": [{"range": {"start": posicao(texto, indice), "end": posicao(texto, indice + 6)},
                            "text": ")"}]})
    confira(bool(c.diagnosticos(uri, 2)), "edição incremental após emoji foi ignorada")


@caso("conclusao-de-globais", "conclusoes", capacidade="completionProvider")
def conclusao_globais(c, contexto):
    texto = "mos"
    uri = c.abra(texto)
    labels = conclusoes(c.solicite("textDocument/completion", c.no_ponto(uri, texto, "mos", dentro=3)))
    confira("mostre" in labels, "global mostre ausente")


@caso("conclusao-api-c", "conclusoes", capacidade="completionProvider")
def conclusao_c(c, contexto):
    texto = "tabela."
    uri = c.abra(texto)
    labels = conclusoes(c.solicite("textDocument/completion", c.no_ponto(uri, texto, "tabela.", dentro=7)))
    confira(bool(labels & {"concatene", "tabela.concatene"}), "API C da tabela ausente")


@caso("conclusao-api-fe-com-alias", "conclusoes", capacidade="completionProvider")
def conclusao_fe(c, contexto):
    texto = 'local Correio = importe "correio.imap"\nCorreio.'
    uri = c.abra(texto)
    labels = conclusoes(c.solicite("textDocument/completion", c.no_ponto(uri, texto, "Correio.", dentro=8)))
    # Rótulos definidos pelo catálogo auditado do próprio projeto, não inventados pelo teste.
    manifesto = json.loads((contexto["repositorio"] / "extensões/vscode/api-publica.json").read_text(encoding="utf-8"))
    nomes = {item["rótulo"].split(".")[-1] for item in manifesto["itens"]
             if item["rótulo"].startswith("correio.imap.")}
    confira(bool(nomes), "fixture API Fé precisa acompanhar catálogo público")
    confira(bool(nomes & {label.split(".")[-1] for label in labels}), "alias de biblioteca Fé não resolvido")


@caso("conclusao-respeita-escopo", "escopos", capacidade="completionProvider")
def conclusao_escopo(c, contexto):
    texto = "local visivel = 1\ninício\n    local visivelInterna = 2\nfim\nvis"
    uri = c.abra(texto)
    labels = conclusoes(c.solicite("textDocument/completion", c.no_ponto(uri, texto, "vis", ultimo=True, dentro=3)))
    confira("visivel" in labels and "visivelInterna" not in labels, "variável de outro escopo vazou")


@caso("hover-documenta-global", "ajuda", capacidade="hoverProvider")
def hover_global(c, contexto):
    texto = 'mostre(tamanho("ação"))'
    uri = c.abra(texto)
    ajuda = texto_hover(c.solicite("textDocument/hover", c.no_ponto(uri, texto, "tamanho", dentro=2)))
    confira("grafema" in ajuda.lower(), "hover de tamanho não explica o contrato de grafemas")


@caso("ajuda-de-parametros", "ajuda", capacidade="signatureHelpProvider")
def assinatura(c, contexto):
    texto = "local função somar(primeiro, segundo)\n    retorne primeiro + segundo\nfim\nsomar(1, "
    uri = c.abra(texto)
    resposta = c.solicite("textDocument/signatureHelp", {"textDocument": {"uri": uri},
                                                        "position": posicao(texto, len(texto))})
    confira(resposta and resposta.get("signatures"), "assinatura ausente")
    assinatura = resposta["signatures"][resposta.get("activeSignature", 0)]
    confira("segundo" in assinatura["label"], "parâmetros não extraídos do fonte")
    confira(assinatura.get("activeParameter", resposta.get("activeParameter")) == 1,
            "parâmetro ativo não acompanha a vírgula")


SOMBRA = '''local índice = 1
início
    local índice = 2
    mostre(índice)
fim
mostre(índice)
-- índice deve permanecer no comentário
local texto = "índice deve permanecer no colar"
'''


@caso("definicao-com-sombreamento", "navegacao", capacidade="definitionProvider")
def definicao(c, contexto):
    uri = c.abra(SOMBRA)
    resposta = c.solicite("textDocument/definition", c.no_ponto(uri, SOMBRA, "índice)", dentro=2))
    locais = localizacoes(resposta)
    confira(len(locais) == 1, "definição ambígua para variável local")
    alvo_uri, intervalo = locais[0]
    confira(alvo_uri == uri and intervalo["start"]["line"] == 2 and recorte(SOMBRA, intervalo) == "índice",
            "definição aponta para o índice de outro escopo")


@caso("referencias-excluem-comentarios-colares-e-sombra", "navegacao", capacidade="referencesProvider")
def referencias(c, contexto):
    uri = c.abra(SOMBRA)
    parametros = c.no_ponto(uri, SOMBRA, "índice", dentro=2)
    parametros["context"] = {"includeDeclaration": True}
    locais = localizacoes(c.solicite("textDocument/references", parametros))
    confira(len(locais) == 2 and {intervalo["start"]["line"] for _, intervalo in locais} == {0, 5},
            "referências não respeitam o vínculo da variável")
    confira(all(alvo == uri and recorte(SOMBRA, intervalo) == "índice" for alvo, intervalo in locais),
            "intervalo de referência inválido")


@caso("renomeacao-segura-com-unicode", "refatoracao", capacidade="renameProvider")
def renomeacao(c, contexto):
    uri = c.abra(SOMBRA)
    parametros = c.no_ponto(uri, SOMBRA, "índice", dentro=2)
    parametros["newName"] = "posição"
    edicoes = edicoes_por_uri(c.solicite("textDocument/rename", parametros))
    confira(set(edicoes) == {uri}, "rename alterou arquivos indevidos")
    esperado = SOMBRA.replace("local índice = 1", "local posição = 1").replace("fim\nmostre(índice)", "fim\nmostre(posição)")
    confira(aplique_edicoes(SOMBRA, edicoes[uri]) == esperado, "rename corrompeu escopos, comentário ou colar")
    confira((c.raiz / "principal.fé").read_text(encoding="utf-8") == SOMBRA, "servidor aplicou a edição sem aprovação do cliente")


@caso("renomeacao-recusa-palavra-reservada", "refatoracao", capacidade="renameProvider")
def rename_invalido(c, contexto):
    uri = c.abra(SOMBRA)
    parametros = c.no_ponto(uri, SOMBRA, "índice", dentro=2)
    parametros["newName"] = "fim"
    resposta = c.solicite_bruto("textDocument/rename", parametros)
    confira("error" in resposta or resposta.get("result") is None, "rename gerou fonte inválido usando palavra reservada")


@caso("renomeacao-inclui-dois-curingas", "refatoracao", capacidade="renameProvider")
def rename_gabaritos(c, contexto):
    texto = 'local nome = "Ana"\nlocal s = `®nome Ⓡnome ®{nome} Ⓡ{nome} nome`\n'
    uri = c.abra(texto)
    parametros = c.no_ponto(uri, texto, "nome", dentro=1)
    parametros["newName"] = "pessoa"
    edicoes = edicoes_por_uri(c.solicite("textDocument/rename", parametros))
    esperado = 'local pessoa = "Ana"\nlocal s = `®pessoa Ⓡpessoa ®{pessoa} Ⓡ{pessoa} nome`\n'
    confira(set(edicoes) == {uri} and aplique_edicoes(texto, edicoes[uri]) == esperado,
            "rename deve distinguir interpolação de texto literal, com ® e Ⓡ")


def modulo(c):
    caminho = c.raiz / "calculadora.fé"
    texto = 'local M = {}\nfunção M.somar(a, b) retorne a + b fim\nretorne M\n'
    caminho.write_text(texto, encoding="utf-8")
    principal = 'local Calc = importe "calculadora"\nmostre(Calc.somar(1, 2))\n'
    uri = c.abra(principal)
    return caminho, texto, uri, principal


@caso("definicao-em-modulo-nao-aberto", "importacoes", capacidade="definitionProvider")
def definicao_modulo(c, contexto):
    caminho, texto, uri, principal = modulo(c)
    locais = localizacoes(c.solicite("textDocument/definition", c.no_ponto(uri, principal, "somar", dentro=2)))
    confira(len(locais) == 1 and locais[0][0] == caminho.as_uri() and recorte(texto, locais[0][1]) == "somar",
            "importação estática de módulo não aberto não resolvida")


@caso("renomeacao-entre-arquivos", "refatoracao", capacidade="renameProvider")
def rename_modulo(c, contexto):
    caminho, texto, uri, principal = modulo(c)
    parametros = c.no_ponto(uri, principal, "somar", dentro=2)
    parametros["newName"] = "adicionar"
    edicoes = edicoes_por_uri(c.solicite("textDocument/rename", parametros))
    confira(set(edicoes) == {uri, caminho.as_uri()}, "rename não abrange definição e uso no projeto")
    confira(aplique_edicoes(texto, edicoes[caminho.as_uri()]) == texto.replace("somar", "adicionar"), "definição não renomeada")
    confira(aplique_edicoes(principal, edicoes[uri]) == principal.replace("somar", "adicionar"), "uso não renomeado")


@caso("importacao-sem-efeitos-colaterais-na-complecao", "seguranca", capacidade="completionProvider")
def modulo_sem_execucao(c, contexto):
    (c.raiz / "perigoso.fé").write_text('local a = es.abra("modulo-executado", "w"); a:escreva("erro")\n'
                                      'local M = {}\nfunção M.consultar() retorne 42 fim\nretorne M\n', encoding="utf-8")
    texto = 'local M = importe "perigoso"\nM.'
    uri = c.abra(texto)
    labels = conclusoes(c.solicite("textDocument/completion", c.no_ponto(uri, texto, "M.", dentro=2)))
    confira(bool(labels & {"consultar", "M.consultar"}), "exportação estática não encontrada")
    confira(not (c.raiz / "modulo-executado").exists(), "SLS executou módulo para obter conclusões")


@caso("invalidacao-de-modulo-alterado", "importacoes", capacidade="definitionProvider")
def invalidacao(c, contexto):
    caminho, texto, uri, principal = modulo(c)
    c.solicite("textDocument/definition", c.no_ponto(uri, principal, "somar", dentro=2))
    novo = "-- nova linha\n" + texto
    caminho.write_text(novo, encoding="utf-8")
    c.notifique("workspace/didChangeWatchedFiles", {"changes": [{"uri": caminho.as_uri(), "type": 2}]})
    locais = localizacoes(c.solicite("textDocument/definition", c.no_ponto(uri, principal, "somar", dentro=2)))
    confira(len(locais) == 1 and locais[0][1]["start"]["line"] == 2, "índice do projeto ficou desatualizado")


@caso("simbolos-do-documento", "navegacao", capacidade="documentSymbolProvider")
def simbolos_documento(c, contexto):
    uri = c.abra("local função externa()\n    local função interna() retorne 1 fim\n    retorne interna()\nfim\n")
    nomes = nomes_simbolos(c.solicite("textDocument/documentSymbol", {"textDocument": {"uri": uri}}))
    confira({"externa", "interna"}.issubset(nomes), "estrutura de funções incompleta")


@caso("simbolos-do-projeto", "navegacao", capacidade="workspaceSymbolProvider")
def simbolos_projeto(c, contexto):
    c.abra("função consultar() retorne 42 fim\n", "outro.fé")
    nomes = nomes_simbolos(c.solicite("workspace/symbol", {"query": "consultar"}))
    confira("consultar" in nomes, "busca de símbolos do projeto não encontrou função")


@caso("destaques-respeitam-escopo", "navegacao", capacidade="documentHighlightProvider")
def destaques(c, contexto):
    uri = c.abra(SOMBRA)
    itens = c.solicite("textDocument/documentHighlight", c.no_ponto(uri, SOMBRA, "índice", dentro=2))
    confira(isinstance(itens, list) and len(itens) == 2 and
            {item["range"]["start"]["line"] for item in itens} == {0, 5}, "destaques incluem outra variável")


@caso("dobramento-de-blocos", "edicao", capacidade="foldingRangeProvider")
def dobramento(c, contexto):
    uri = c.abra("local função externa()\n    mostre(1)\n    mostre(2)\nfim\n")
    itens = c.solicite("textDocument/foldingRange", {"textDocument": {"uri": uri}})
    confira(itens and any(item["startLine"] == 0 and item["endLine"] in (2, 3) for item in itens), "bloco de função não dobrável")


@caso("selecao-estrutural", "edicao", capacidade="selectionRangeProvider")
def selecao(c, contexto):
    texto = "local valor = (1 + 2)\n"
    uri = c.abra(texto)
    itens = c.solicite("textDocument/selectionRange", {"textDocument": {"uri": uri},
                                                     "positions": [posicao(texto, texto.index("1"))]})
    confira(isinstance(itens, list) and len(itens) == 1, "selectionRange não corresponde ao pedido")
    item, anterior, quantidade = itens[0], None, 0
    while item:
        atual = (deslocamento(texto, item["range"]["start"]), deslocamento(texto, item["range"]["end"]))
        confira(atual[0] <= texto.index("1") < atual[1], "seleção não contém o cursor")
        if anterior:
            confira(atual[0] <= anterior[0] and atual[1] >= anterior[1], "seleções não estão aninhadas")
        anterior, item = atual, item.get("parent")
        quantidade += 1
        confira(quantidade < 30, "cadeia de seleções excessiva")
    confira(quantidade >= 2, "faltam expansões estruturais de seleção")


@caso("formatacao-idempotente-preserva-colares", "formatacao", capacidade="documentFormattingProvider")
def formatacao(c, contexto):
    texto = '''local função pagina(nome)
local html = [[<a title="]] .. nome .. [[">ação 🟢</a>]]
-- comentário preservado
retorne `®nome Ⓡ{nome}`, html
fim
'''
    candidato = ("dados." in c.informacao.get("version", "") or c.informacao.get("version") == "1.1.0")
    if candidato:
        texto = texto.replace('[[', '[=[').replace(']]', ']=]')
    uri = c.abra(texto)
    parametros = {"textDocument": {"uri": uri}, "options": {"tabSize": 4, "insertSpaces": True}}
    edicoes = c.solicite("textDocument/formatting", parametros)
    confira(isinstance(edicoes, list) and bool(edicoes), "formatador não ajustou bloco sem indentação")
    novo = aplique_edicoes(texto, edicoes)
    confira(novo != texto and "\n    local html" in novo, "indentação da função não corrigida")
    for fragmento in ['[[<a title="]]', '[[">ação 🟢</a>]]', '`®nome Ⓡ{nome}`', '-- comentário preservado']:
        if candidato:
            fragmento = fragmento.replace('[[', '[=[').replace(']]', ']=]')
        confira(fragmento in novo, "formatação alterou texto literal/comentário: " + fragmento)
    c.mude(uri, novo)
    confira(c.diagnosticos(uri, 2) == [], "formatador produziu fonte inválido")
    confira(aplique_edicoes(novo, c.solicite("textDocument/formatting", parametros) or []) == novo, "formatação não é idempotente")


@caso("formatacao-preserva-crlf", "formatacao", capacidade="documentFormattingProvider")
def formato_crlf(c, contexto):
    texto = "local função f()\r\nmostre(42)\r\nfim\r\n"
    uri = c.abra(texto)
    edicoes = c.solicite("textDocument/formatting", {"textDocument": {"uri": uri},
                                                   "options": {"tabSize": 4, "insertSpaces": True}})
    novo = aplique_edicoes(texto, edicoes)
    confira("\r\n    mostre" in novo and "\n" not in novo.replace("\r\n", ""), "formatação perdeu CRLF")


@caso("acao-de-codigo-fim-ausente", "acoes", capacidade="codeActionProvider")
def acao(c, contexto):
    texto = "local função exemplo()\n    retorne 42\n"
    uri = c.abra(texto)
    erros = c.diagnosticos(uri, 1)
    confira(bool(erros), "diagnóstico da fixture ausente")
    acoes = c.solicite("textDocument/codeAction", {"textDocument": {"uri": uri}, "range": erros[0]["range"],
                                                "context": {"diagnostics": erros, "only": ["quickfix"]}})
    candidatas = [item for item in acoes or [] if item.get("edit") and not item.get("disabled")]
    confira(bool(candidatas), "quickfix precisa fornecer edição revisável, não executar comando")
    resolveu = False
    for item in candidatas:
        edicoes = edicoes_por_uri(item["edit"])
        confira(set(edicoes) == {uri}, "quickfix afetou documento alheio")
        novo = aplique_edicoes(texto, edicoes[uri])
        versao = c.mude(uri, novo)
        if c.diagnosticos(uri, versao) == []:
            resolveu = True
            break
    confira(resolveu, "nenhuma correção oferecida fecha a função")


@caso("tokens-semanticamente-distinguem-gabaritos", "realce", capacidade="semanticTokensProvider")
def tokens(c, contexto):
    capacidade = c.capacidades["semanticTokensProvider"]
    if capacidade.get("full") is None or capacidade.get("full") is False:
        raise Pendente("tokens semânticos completos não anunciados")
    texto = 'local nome = "Ana"\nlocal s = `®nome Ⓡnome ®{nome} Ⓡ{nome}`\n'
    uri = c.abra(texto)
    resposta = c.solicite("textDocument/semanticTokens/full", {"textDocument": {"uri": uri}})
    dados = resposta.get("data", []) if isinstance(resposta, dict) else []
    confira(bool(dados) and len(dados) % 5 == 0, "fluxo de tokens semânticos inválido")
    legenda = capacidade["legend"]["tokenTypes"]
    linha = coluna = 0
    encontrados = []
    for i in range(0, len(dados), 5):
        delta, caractere, tamanho, tipo, modificadores = dados[i:i + 5]
        confira(all(type(n) is int and n >= 0 for n in (delta, caractere, tamanho, tipo, modificadores)), "token negativo/não inteiro")
        linha += delta
        coluna = caractere if delta else coluna + caractere
        confira(tamanho > 0 and tipo < len(legenda), "tipo/comprimento de token inválido")
        trecho = recorte(texto, {"start": {"line": linha, "character": coluna},
                                "end": {"line": linha, "character": coluna + tamanho}})
        if "nome" in trecho and legenda[tipo] == "variable":
            encontrados.append((linha, coluna))
    confira(len(encontrados) == 5, "declaração e quatro interpolações precisam ser variáveis, não colares")


@caso("cancelamento-nao-derruba-sessao", "protocolo", "atual")
def cancelamento(c, contexto):
    # Cancelar pedido inexistente é inofensivo; cancelamento de análise longa é gate adicional de carga.
    c.notifique("$/cancelRequest", {"id": 99999})
    uri = c.abra("mostre(42)")
    confira(c.diagnosticos(uri, 1) == [], "cancelamento desconhecido encerrou sessão")
