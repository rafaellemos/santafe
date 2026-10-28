#!/usr/bin/env python3
"""Ensaia as conclusões e a ajuda sem iniciar o Sublime Text."""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import tempfile
import types


RAIZ = pathlib.Path(__file__).resolve().parents[1]


class Região:
    def __init__(self, começo: int, fim: int | None = None):
        self._começo = começo
        self._fim = começo if fim is None else fim

    def begin(self) -> int:
        return self._começo

    def end(self) -> int:
        return self._fim

    def empty(self) -> bool:
        return self._começo == self._fim


class Seleções(list):
    def add(self, região):
        self.append(região)


class Configurações(dict):
    def get(self, chave, padrão=None):
        return super().get(chave, padrão)

    def set(self, chave, valor):
        self[chave] = valor


class ComandoDeTexto:
    def __init__(self, view):
        self.view = view


class ComandoDeAplicação:
    pass


class ComandoDeJanela:
    def __init__(self, window):
        self.window = window


class Item:
    def __init__(self, trigger, **kwargs):
        self.trigger = trigger
        self.kwargs = kwargs

    @classmethod
    def snippet_completion(cls, trigger, snippet, **kwargs):
        kwargs["completion"] = snippet
        return cls(trigger, **kwargs)


class Visão:
    def __init__(self, texto: str):
        self.texto = texto
        self.popup = ""
        self.seleções = Seleções([Região(len(texto))])
        self.configurações = Configurações(tab_size=4, translate_tabs_to_spaces=True)
        self.comando_executado = ""

    def match_selector(self, ponto, escopo):
        return escopo in {"source.santafe", "source.santafe - comment - string"}

    def substr(self, região):
        return self.texto[região.begin():região.end()]

    def size(self):
        return len(self.texto)

    def sel(self):
        return self.seleções

    def line(self, ponto):
        começo = self.texto.rfind("\n", 0, ponto) + 1
        fim = self.texto.find("\n", ponto)
        return Região(começo, len(self.texto) if fim == -1 else fim)

    def insert(self, edit, ponto, conteúdo):
        self.texto = self.texto[:ponto] + conteúdo + self.texto[ponto:]

    def settings(self):
        return self.configurações

    def run_command(self, comando, argumentos):
        self.comando_executado = comando

    def word(self, ponto):
        começo = ponto
        fim = ponto
        while começo > 0 and (self.texto[começo - 1].isalnum() or self.texto[começo - 1] == "_"):
            começo -= 1
        while fim < len(self.texto) and (self.texto[fim].isalnum() or self.texto[fim] == "_"):
            fim += 1
        return Região(começo, fim)

    def show_popup(self, conteúdo, **kwargs):
        self.popup = conteúdo


def carregue_módulo():
    sublime = types.ModuleType("sublime")
    sublime.Region = Região
    sublime.CompletionItem = Item
    sublime.KIND_KEYWORD = (1, "k", "Palavra reservada")
    sublime.KIND_NAMESPACE = (4, "n", "Biblioteca")
    sublime.KIND_FUNCTION = (3, "f", "Função")
    sublime.INHIBIT_WORD_COMPLETIONS = 1
    sublime.HOVER_TEXT = 1
    sublime.View = Visão
    configurações = {}
    sublime.configurações = configurações
    sublime.salvas = []
    sublime.erro = ""
    sublime.mensagem = ""
    sublime.status = ""
    sublime.load_resource = lambda _: (RAIZ / "api-publica.json").read_text(encoding="utf-8")
    sublime.load_settings = lambda nome: configurações.setdefault(nome, Configurações())
    sublime.save_settings = lambda nome: sublime.salvas.append(nome)
    sublime.error_message = lambda mensagem: setattr(sublime, "erro", mensagem)
    sublime.message_dialog = lambda mensagem: setattr(sublime, "mensagem", mensagem)
    sublime.status_message = lambda mensagem: setattr(sublime, "status", mensagem)
    plugin = types.ModuleType("sublime_plugin")
    plugin.EventListener = object
    plugin.TextCommand = ComandoDeTexto
    plugin.ApplicationCommand = ComandoDeAplicação
    plugin.WindowCommand = ComandoDeJanela
    sys.modules["sublime"] = sublime
    sys.modules["sublime_plugin"] = plugin
    especificação = importlib.util.spec_from_file_location("Santafe", RAIZ / "Santafe.py")
    módulo = importlib.util.module_from_spec(especificação)
    assert especificação and especificação.loader
    especificação.loader.exec_module(módulo)
    return módulo, sublime


def principal() -> None:
    módulo, sublime = carregue_módulo()
    for nome in ("saudação", "saudac\u0327a\u0303o", "i\u0301ndice", "_ação2"):
        assert módulo.nomes_locais(Visão("local função " + nome + "()\nfim")) == (nome,)
        for final in ("", "valor", "a\u0301"):
            trecho = "mostre(" + nome + "." + final
            assert módulo.acesso_antes_do(Visão(trecho), len(trecho)) == nome + "."
    assert módulo.nomes_locais(Visão("local função \u0301invalida()\nfim")) == ()
    assert módulo.acesso_antes_do(Visão("2invalido."), 10) == ""
    assert len(json.loads((RAIZ / "api-publica.json").read_text(encoding="utf-8"))["itens"]) >= 300
    ouvinte = módulo.SantafeConclusões()
    visão = Visão("local função saudação(nome) início\n    mostre(nome)\nfim\ncorreio.")
    gerais, sinalizadores = ouvinte.on_query_completions(visão, "", [visão.texto.index("mostre")])
    assert sinalizadores == sublime.INHIBIT_WORD_COMPLETIONS
    assert {item.trigger for item in gerais} >= {"mostre", "saudação", "função"}
    função = next(item for item in gerais if item.trigger == "função")
    assert "início" not in função.kwargs["completion"] and "\nfim" in função.kwargs["completion"]
    para = next(item for item in gerais if item.trigger == "para")
    assert "para ${1:índice}" in para.kwargs["completion"] and "\nfim" in para.kwargs["completion"]
    assert módulo.CABEÇALHO_DE_BLOCO.fullmatch("para índice = 1, 10 início")
    assert módulo.CABEÇALHO_DE_BLOCO.fullmatch("para nome em ipares(nomes) início")
    assert not módulo.CABEÇALHO_DE_BLOCO.fullmatch("índice")
    visão_do_laço = Visão("para índice = 1, 10 início")
    módulo.SantafeNovaLinhaCommand(visão_do_laço).run(None)
    assert visão_do_laço.texto == "para índice = 1, 10 início\n    \nfim"
    assert visão_do_laço.seleções[0].begin() == len("para índice = 1, 10 início\n    ")
    for cabeçalho in ("função teste(índice)", "local função teste() início", "    função aninhada()", "se verdadeiro então"):
        v = Visão(cabeçalho)
        módulo.SantafeNovaLinhaCommand(v).run(None)
        recuo = "    " if cabeçalho.startswith("    ") else ""
        assert v.texto == cabeçalho + "\n" + recuo + "    \n" + recuo + "fim"
    v = Visão("função teste()\nfim")
    v.seleções = Seleções([Região(len("função teste()"))])
    módulo.SantafeNovaLinhaCommand(v).run(None)
    assert v.texto.count("fim") == 1
    atalhos = json.loads((RAIZ / "Default.sublime-keymap").read_text())
    assert any(a["keys"] == ["enter"] and a["command"] == "santafe_nova_linha" for a in atalhos)
    with tempfile.TemporaryDirectory() as diretório:
        iniciador = pathlib.Path(diretório) / "santafé-sls"
        iniciador.write_text("#!/bin/sh\n", encoding="utf-8")
        iniciador.chmod(0o755)
        módulo.CAMINHOS_SLS = (str(iniciador),)
        original_which = módulo.shutil.which
        módulo.shutil.which = lambda _: None
        try:
            módulo.SantafeAtivarDiagnosticosSLSCommand().run()
        finally:
            módulo.shutil.which = original_which
        executable = pathlib.Path(diretório) / 'santafé'
        executable.write_text('#!/bin/sh\n')
        executable.chmod(0o755)
        calls = []
        window = types.SimpleNamespace(run_command=lambda name, args: calls.append((name, args)))
        original_which = módulo.shutil.which
        try:
            módulo.shutil.which = lambda _: None
            special_name = '/tmp/carta $(nao_executar); com espaços.fé'
            build = módulo.SantafeExecutarCommand(window)
            build.run(cmd=['santafé', special_name])
            assert calls[-1] == ('exec', {'cmd': [str(executable), special_name]})
            build.run(kill=True)
            assert calls[-1] == ('exec', {'kill': True})
        finally:
            módulo.shutil.which = original_which
    assert sublime.erro == ""
    assert sublime.configurações["LanguageServers.sublime-settings"]["Santafé"]["command"] == [str(iniciador)]
    assert "LSP" in sublime.configurações["Package Control.sublime-settings"]["installed_packages"]
    assert "Package Control.sublime-settings" in sublime.salvas
    assert "Reabra o Sublime Text" in sublime.mensagem
    membros, _ = ouvinte.on_query_completions(visão, "", [len(visão.texto)])
    assert any(item.trigger == "novaMensagem" for item in membros)
    ouvinte.on_hover(visão, visão.texto.index("mostre"), sublime.HOVER_TEXT)
    assert "mostre" in visão.popup and "saída padrão" in visão.popup
    print("Sublime Santafé: conclusões e ajuda: ok")


if __name__ == "__main__":
    principal()
