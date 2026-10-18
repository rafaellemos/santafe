"""Conclui e explica a superfície pública do Santafé no Sublime Text."""

from __future__ import annotations

import html
import json
import os
import re
import shutil

import sublime
import sublime_plugin


ESCOPO = "source.santafe"
RECURSO_DO_CATÁLOGO = "Packages/Santafe/api-publica.json"
ARQUIVO_CONFIGURAÇÕES_LSP = "LanguageServers.sublime-settings"
ARQUIVO_CONFIGURAÇÕES_PACOTES = "Package Control.sublime-settings"
NOME_DO_CLIENTE_LSP = "LSP"
CAMINHOS_SLS = (
    "/usr/local/bin/santafé-sls",
    os.path.expanduser("~/.local/bin/santafé-sls"),
)
INÍCIO_DE_IDENTIFICADOR = r"[^\W\d]"
IDENTIFICADOR = rf"{INÍCIO_DE_IDENTIFICADOR}\w*"
# O membro pode estar vazio: ao escrever `correio.` o editor já deve
# oferecer os membros da biblioteca.  Não acrescente `*` a IDENTIFICADOR,
# pois ele já contém uma repetição para os caracteres restantes.
ACESSO_FINAL = re.compile(rf"((?:{IDENTIFICADOR}[.:])+)(?:{INÍCIO_DE_IDENTIFICADOR}\w*)?$")
FUNÇÃO_LOCAL = re.compile(rf"^\s*(?:local\s+)?função\s+({IDENTIFICADOR})", re.MULTILINE)

PALAVRAS_RESERVADAS = (
    "local", "função", "retorne", "se", "então", "senão", "enquanto",
    "para", "em", "repita", "até", "início", "fim", "pare", "vápara",
    "nulo", "verdadeiro", "falso", "e", "ou", "não",
)

GABARITOS_DE_BLOCO = {
    "função": "função ${1:nome}(${2}) início\n    ${0}\nfim",
    "se": "se ${1:condição} então\n    ${0}\nfim",
    "para": "para ${1:índice} = ${2:1}, ${3:10} início\n    ${0}\nfim",
    "enquanto": "enquanto ${1:condição} início\n    ${0}\nfim",
    "repita": "repita\n    ${0}\naté ${1:condição}",
}

# O Sublime cuida do recuo, mas não cria automaticamente o fim de um bloco.
# Esta expressão só aceita cabeçalhos completos, no fim da linha: assim um
# Enter normal permanece normal e não cria um `fim` por engano no meio de
# código, comentário ou colar.
CABEÇALHO_DE_BLOCO = re.compile(
    r"^(?P<recuo>[ \t]*)(?:"
    r"(?:local\s+)?função\b.+\)(?:\s+início)?|"
    r"se\b.+\bentão\b|"
    r"(?:para|enquanto)\b.+\binício\b"
    r")(?:\s*--.*)?$"
)

FUNÇÕES_DO_NÚCLEO = (
    ("mostre", "Exibe valores na saída padrão.", "mostre(${1})"),
    ("tipo", "Devolve o tipo lógico de um valor.", "tipo(${1:valor})"),
    ("tamanho", "Conta grafemas de um colar; em tabelas, segue #.", "tamanho(${1:valor})"),
    ("octetos", "Mede os octetos de um colar.", "octetos(${1:dados})"),
    ("importe", "Carrega uma biblioteca Santafé.", "importe \"${1:biblioteca}\""),
    ("carregue", "Compila um colar sem o executar.", "carregue(${1:fonte})"),
    ("carregueArquivo", "Compila um arquivo sem o executar.", "carregueArquivo(${1:caminho})"),
    ("executeArquivo", "Executa um arquivo Santafé.", "executeArquivo(${1:caminho})"),
    ("garanta", "Interrompe quando a condição não é verdadeira.", "garanta(${1:condição}, ${2:mensagem})"),
    ("proteja", "Executa uma função protegida.", "proteja(função()\n    ${0}\nfim)"),
    ("protejaMais", "Executa uma função com tratador de falhas.", "protejaMais(${1:função}, ${2:tratador})"),
    ("paraNúmero", "Converte um valor em número quando possível.", "paraNúmero(${1:valor})"),
    ("paraColar", "Converte um valor em colar.", "paraColar(${1:valor})"),
    ("pares", "Itera as chaves de uma tabela.", "pares(${1:tabela})"),
    ("ipares", "Itera a sequência numérica inicial de uma tabela.", "ipares(${1:tabela})"),
    ("próximo", "Avança manualmente sobre as chaves de uma tabela.", "próximo(${1:tabela})"),
    ("erro", "Interrompe a execução com uma falha.", "erro(${1:mensagem})"),
    ("coleteLixo", "Controla o coletor de lixo.", "coleteLixo(${1:opção})"),
)

BIBLIOTECAS = (
    "arquivo", "bit32", "caminheiro", "colar", "correio", "es", "imagem",
    "json", "mariadb", "mat", "nomes", "pulso", "rede", "rpdf", "segredo",
    "tomada", "turing", "vigia", "so", "tabela", "utf8", "corrotina", "depure", "módulo",
)


def leia_catálogo():
    try:
        bruto = sublime.load_resource(RECURSO_DO_CATÁLOGO)
        catálogo = json.loads(bruto)
        itens = catálogo.get("itens", [])
        return tuple(item for item in itens if isinstance(item, dict) and isinstance(item.get("rótulo"), str))
    except (OSError, ValueError, TypeError):
        return ()


CATÁLOGO_PÚBLICO = leia_catálogo()
INFORMAÇÕES = {
    nome: {"rótulo": nome, "categoria": "função global", "documentação": documentação}
    for nome, documentação, _ in FUNÇÕES_DO_NÚCLEO
}
for item in CATÁLOGO_PÚBLICO:
    INFORMAÇÕES.setdefault(item["rótulo"], {
        "rótulo": item["rótulo"],
        "categoria": item.get("categoria", "API pública"),
        "documentação": f"API pública em {item.get('origem', 'biblioteca Santafé')}."
    })


def acesso_antes_do(view: sublime.View, ponto: int) -> str:
    começo = max(0, ponto - 256)
    trecho = view.substr(sublime.Region(começo, ponto))
    encontrado = ACESSO_FINAL.search(trecho)
    return encontrado.group(1) if encontrado else ""


def nomes_locais(view: sublime.View) -> tuple[str, ...]:
    return tuple(sorted({encontrado.group(1) for encontrado in FUNÇÃO_LOCAL.finditer(view.substr(sublime.Region(0, view.size())))}, key=str.casefold))


def item_de_conclusão(rótulo, anotação, espécie, conteúdo=None, detalhes=""):
    argumentos = {
        "annotation": anotação,
        "kind": espécie,
        "details": detalhes or anotação,
    }
    if conteúdo and "${" in conteúdo:
        return sublime.CompletionItem.snippet_completion(rótulo, conteúdo, **argumentos)
    argumentos["completion"] = conteúdo or rótulo
    return sublime.CompletionItem(rótulo, **argumentos)


class SantafeNovaLinhaCommand(sublime_plugin.TextCommand):
    """Fecha um bloco ao pressionar Enter depois de seu cabeçalho completo."""

    def run(self, edit):
        seleções = self.view.sel()
        if len(seleções) != 1 or not seleções[0].empty():
            self._insira_nova_linha()
            return

        ponto = seleções[0].begin()
        if not self.view.match_selector(ponto, ESCOPO + " - comment - string"):
            self._insira_nova_linha()
            return

        linha = self.view.line(ponto)
        if ponto != linha.end():
            self._insira_nova_linha()
            return

        cabeçalho = self.view.substr(linha)
        encontrado = CABEÇALHO_DE_BLOCO.fullmatch(cabeçalho)
        if not encontrado:
            self._insira_nova_linha()
            return

        recuo = encontrado.group("recuo")
        tabulação = self._tabulação()
        restante = self.view.substr(sublime.Region(ponto, self.view.size()))
        tem_fim = re.match(r"\n" + re.escape(recuo) + r"fim\s*(?:\n|$)", restante)
        inserção = "\n{}{}".format(recuo, tabulação)
        if not tem_fim:
            inserção += "\n{}fim".format(recuo)
        self.view.insert(edit, ponto, inserção)
        seleções.clear()
        seleções.add(sublime.Region(ponto + 1 + len(recuo) + len(tabulação)))

    def _tabulação(self):
        configurações = self.view.settings()
        if configurações.get("translate_tabs_to_spaces") is False:
            return "\t"
        return " " * int(configurações.get("tab_size", 4))

    def _insira_nova_linha(self):
        self.view.run_command("insert", {"characters": "\n"})


def caminho_do_sls():
    """Devolve um iniciador instalado, sem depender do PATH do aplicativo."""
    for caminho in CAMINHOS_SLS:
        if os.path.isfile(caminho) and os.access(caminho, os.X_OK):
            return caminho
    return ""


class SantafeExecutarCommand(sublime_plugin.WindowCommand):
    """Executa com argumentos separados, sem interpretar o nome do arquivo como shell."""

    def run(self, cmd=None, kill=False, **options):
        if kill:
            self.window.run_command("exec", {"kill": True})
            return
        if not cmd:
            return
        command = list(cmd)
        executable = shutil.which(command[0])
        if not executable:
            for launcher in CAMINHOS_SLS:
                candidate = os.path.join(os.path.dirname(launcher), command[0])
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    executable = candidate
                    break
        if not executable:
            sublime.error_message("Instale o núcleo Santafé antes de executar este arquivo.")
            return
        command[0] = executable
        options["cmd"] = command
        self.window.run_command("exec", options)


class SantafeAtivarDiagnosticosSLSCommand(sublime_plugin.ApplicationCommand):
    """Configura o SLS e pede ao Package Control o cliente LSP necessário."""

    def run(self):
        iniciador = caminho_do_sls()
        if not iniciador:
            sublime.error_message(
                "O núcleo Santafé ainda não está instalado. Instale a distribuição "
                "oficial antes de ativar os diagnósticos SLS."
            )
            return

        configurações_lsp = sublime.load_settings(ARQUIVO_CONFIGURAÇÕES_LSP)
        configurações_lsp.set("Santafé", {
            "enabled": True,
            "command": [iniciador],
            "selector": ESCOPO,
            "schemes": ["file", "buffer"],
            "diagnostics_mode": "workspace",
        })
        sublime.save_settings(ARQUIVO_CONFIGURAÇÕES_LSP)

        configurações_pacotes = sublime.load_settings(ARQUIVO_CONFIGURAÇÕES_PACOTES)
        pacotes = list(configurações_pacotes.get("installed_packages") or [])
        instalou_cliente = NOME_DO_CLIENTE_LSP not in pacotes
        if instalou_cliente:
            pacotes.append(NOME_DO_CLIENTE_LSP)
            configurações_pacotes.set("installed_packages", pacotes)
            sublime.save_settings(ARQUIVO_CONFIGURAÇÕES_PACOTES)

        if instalou_cliente:
            sublime.message_dialog(
                "O cliente LSP foi incluído para instalação pelo Package Control. "
                "Reabra o Sublime Text para concluir a ativação do SLS."
            )
        else:
            sublime.status_message("Santafé: diagnósticos SLS ativados.")


class SantafeConclusões(sublime_plugin.EventListener):
    """Conclusões locais e da API pública, sem depender do cliente LSP."""

    def on_query_completions(self, view, prefix, locations):
        if not locations or not view.match_selector(locations[0], ESCOPO):
            return None

        acesso = acesso_antes_do(view, locations[0])
        itens = []
        if not acesso:
            itens.extend(
                item_de_conclusão(
                    palavra,
                    "estrutura de bloco" if palavra in GABARITOS_DE_BLOCO else "palavra reservada",
                    sublime.KIND_KEYWORD,
                    GABARITOS_DE_BLOCO.get(palavra),
                )
                for palavra in PALAVRAS_RESERVADAS
            )
            itens.extend(item_de_conclusão(biblioteca, "biblioteca Santafé", sublime.KIND_NAMESPACE) for biblioteca in BIBLIOTECAS)
            itens.extend(item_de_conclusão(nome, "função deste arquivo", sublime.KIND_FUNCTION) for nome in nomes_locais(view))

        inserções = {nome: inserção for nome, _, inserção in FUNÇÕES_DO_NÚCLEO}
        for nome, informação in INFORMAÇÕES.items():
            if acesso and not nome.startswith(acesso):
                continue
            rótulo = nome[len(acesso):] if acesso else nome
            anotação = f"{nome} — {informação['categoria']}" if acesso else informação["categoria"]
            itens.append(item_de_conclusão(
                rótulo,
                anotação,
                sublime.KIND_FUNCTION,
                None if acesso else inserções.get(nome),
                informação["documentação"],
            ))
        return (itens, sublime.INHIBIT_WORD_COMPLETIONS)

    def on_hover(self, view, point, hover_zone):
        if hover_zone != sublime.HOVER_TEXT or not view.match_selector(point, ESCOPO):
            return
        palavra = view.substr(view.word(point))
        if not palavra:
            return
        acesso = acesso_antes_do(view, view.word(point).begin())
        informação = INFORMAÇÕES.get(acesso + palavra) or INFORMAÇÕES.get(palavra)
        if not informação:
            return
        rótulo = html.escape(informação["rótulo"])
        categoria = html.escape(informação["categoria"])
        documentação = html.escape(informação["documentação"])
        view.show_popup(
            f"<body><h3>{rótulo}</h3><p><b>{categoria}</b></p><p>{documentação}</p></body>",
            location=point,
            max_width=520,
        )
