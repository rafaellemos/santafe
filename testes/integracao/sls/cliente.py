"""Cliente LSP de teste: prazos, quadros limitados e encerramento garantido.

Não usa o código do cliente VS Code: um defeito compartilhado por cliente e
servidor não deve tornar a bateria verde. Só inicia o comando explicitamente
selecionado e só cria documentos em um TemporaryDirectory do ensaio.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import queue
import subprocess
import threading
import time
from typing import Any


LIMITE = 16 * 1024 * 1024


class FalhaLsp(AssertionError):
    pass


class Pendente(Exception):
    """Capacidade não anunciada: não é um teste aprovado nem ignorado."""


def quadro(mensagem: Any) -> bytes:
    corpo = json.dumps(mensagem, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return b"Content-Length: " + str(len(corpo)).encode("ascii") + b"\r\n\r\n" + corpo


def leia_quadro(saida):
    tamanho = None
    lidos = 0
    while True:
        linha = saida.readline(8193)
        if not linha:
            raise FalhaLsp("EOF antes de uma resposta LSP completa")
        lidos += len(linha)
        if lidos > 8192 or not linha.endswith(b"\n"):
            raise FalhaLsp("cabeçalho da resposta excede o limite")
        if linha in (b"\r\n", b"\n"):
            break
        if b":" not in linha:
            raise FalhaLsp("stdout contém texto que não pertence ao protocolo")
        nome, valor = linha.rstrip(b"\r\n").split(b":", 1)
        if nome.lower() == b"content-length":
            if tamanho is not None or not valor.strip().isdigit():
                raise FalhaLsp("Content-Length duplicado ou inválido na resposta")
            tamanho = int(valor.strip())
    if tamanho is None or not 0 < tamanho <= LIMITE:
        raise FalhaLsp("resposta sem Content-Length válido")
    corpo = bytearray()
    while len(corpo) < tamanho:
        parte = saida.read(tamanho - len(corpo))
        if not parte:
            raise FalhaLsp("resposta truncada")
        corpo.extend(parte)
    try:
        mensagem = json.loads(corpo.decode("utf-8"))
    except (ValueError, UnicodeError) as erro:
        raise FalhaLsp("resposta JSON/UTF-8 inválida") from erro
    if not isinstance(mensagem, dict) or mensagem.get("jsonrpc") != "2.0":
        raise FalhaLsp("envelope de resposta JSON-RPC inválido")
    return mensagem


def posicao(texto: str, deslocamento: int) -> dict:
    """Índice Python → posição LSP UTF-16 (não bytes nem grafemas)."""
    if not 0 <= deslocamento <= len(texto):
        raise FalhaLsp("deslocamento fora do documento")
    inicio = texto.rfind("\n", 0, deslocamento) + 1
    return {"line": texto.count("\n", 0, deslocamento),
            "character": len(texto[inicio:deslocamento].encode("utf-16-le")) // 2}


def deslocamento(texto: str, pos: dict) -> int:
    linha, coluna = pos.get("line"), pos.get("character")
    if type(linha) is not int or type(coluna) is not int or min(linha, coluna) < 0:
        raise FalhaLsp("posição LSP inválida")
    linhas = texto.split("\n")
    if linha >= len(linhas):
        raise FalhaLsp("linha LSP fora do documento")
    atual = linhas[linha].removesuffix("\r")
    unidades = 0
    for indice, caractere in enumerate(atual):
        if unidades == coluna:
            return sum(len(parte) + 1 for parte in linhas[:linha]) + indice
        unidades += len(caractere.encode("utf-16-le")) // 2
        if unidades > coluna:
            raise FalhaLsp("posição LSP corta um par substituto UTF-16")
    if unidades != coluna:
        raise FalhaLsp("coluna LSP fora da linha")
    return sum(len(parte) + 1 for parte in linhas[:linha]) + len(atual)


def recorte(texto: str, intervalo: dict) -> str:
    inicio = deslocamento(texto, intervalo["start"])
    fim = deslocamento(texto, intervalo["end"])
    if fim < inicio:
        raise FalhaLsp("intervalo LSP invertido")
    return texto[inicio:fim]


def aplique_edicoes(texto: str, edicoes: list) -> str:
    """Valida antes de aplicar; nunca altera arquivos do usuário."""
    intervalos = []
    for edicao in edicoes:
        inicio = deslocamento(texto, edicao["range"]["start"])
        fim = deslocamento(texto, edicao["range"]["end"])
        if inicio > fim or not isinstance(edicao.get("newText"), str):
            raise FalhaLsp("TextEdit inválido")
        intervalos.append((inicio, fim, edicao["newText"]))
    intervalos.sort(key=lambda item: (item[0], item[1]))
    for anterior, seguinte in zip(intervalos, intervalos[1:]):
        if anterior[1] > seguinte[0] or anterior[0] == seguinte[0]:
            raise FalhaLsp("edições sobrepostas ou ambíguas")
    for inicio, fim, novo in reversed(intervalos):
        texto = texto[:inicio] + novo + texto[fim:]
    return texto


def edicoes_por_uri(resposta: dict) -> dict:
    if not isinstance(resposta, dict):
        raise FalhaLsp("WorkspaceEdit ausente")
    if "changes" in resposta and "documentChanges" in resposta:
        raise FalhaLsp("o ensaio exige uma única representação de WorkspaceEdit")
    if "changes" in resposta:
        return resposta["changes"]
    saida = {}
    for item in resposta.get("documentChanges", []):
        if "kind" in item:
            raise FalhaLsp("renomear símbolo não pode criar/remover arquivos")
        uri = item["textDocument"]["uri"]
        if uri in saida:
            raise FalhaLsp("documento repetido em WorkspaceEdit")
        saida[uri] = item["edits"]
    return saida


class Cliente:
    def __init__(self, comando: list, raiz: Path, prazo: float = 5.0):
        self.raiz, self.prazo = raiz, prazo
        self.fila = queue.Queue(maxsize=1024)
        self.pendentes = []
        self.contador = 0
        self.documentos = {}
        self.capacidades = {}
        self.informacao = {}
        self.iniciado = False
        self.erros = bytearray()
        # Não herdar caminhos de módulos/segredos de um ambiente de produção.
        ambiente = {chave: valor for chave, valor in os.environ.items()
                    if chave in ("PATH", "HOME", "TMPDIR", "SYSTEMROOT", "WINDIR", "LANG", "LC_ALL")}
        ambiente["GSETTINGS_BACKEND"] = "memory"
        self.processo = subprocess.Popen(comando, cwd=str(raiz), env=ambiente,
                                         stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE)
        self.leitor = threading.Thread(target=self._leia, daemon=True)
        self.leitor_erros = threading.Thread(target=self._leia_erros, daemon=True)
        self.leitor.start()
        self.leitor_erros.start()
        # Também cobre uma escrita bloqueada em stdin. Independe do timeout de leitura.
        self.vigia = threading.Timer(max(15.0, prazo * 8), self._mate)
        self.vigia.daemon = True
        self.vigia.start()

    def _mate(self):
        if self.processo.poll() is None:
            self.processo.kill()

    def _leia(self):
        try:
            while True:
                mensagem = leia_quadro(self.processo.stdout)
                try:
                    self.fila.put(mensagem, timeout=self.prazo)
                except queue.Full as erro:
                    self._mate()
                    raise FalhaLsp("excesso de respostas do servidor") from erro
        except Exception as erro:
            try:
                self.fila.put_nowait(erro)
            except queue.Full:
                # Processo já encerrado; não deixar thread presa durante a limpeza.
                self._mate()

    def _leia_erros(self):
        while True:
            trecho = self.processo.stderr.read(4096)
            if not trecho:
                break
            if len(self.erros) < 65536:
                self.erros.extend(trecho[:65536 - len(self.erros)])

    def envie(self, mensagem):
        self.processo.stdin.write(quadro(mensagem))
        self.processo.stdin.flush()

    def notifique(self, metodo, parametros=None):
        self.envie({"jsonrpc": "2.0", "method": metodo, "params": parametros or {}})

    def receba(self, predicado):
        for indice, mensagem in enumerate(self.pendentes):
            if predicado(mensagem):
                return self.pendentes.pop(indice)
        limite = time.monotonic() + self.prazo
        while True:
            try:
                mensagem = self.fila.get(timeout=max(0, limite - time.monotonic()))
            except queue.Empty as erro:
                raise FalhaLsp("prazo excedido aguardando resposta do SLS") from erro
            if isinstance(mensagem, Exception):
                raise FalhaLsp(str(mensagem)) from mensagem
            if predicado(mensagem):
                return mensagem
            if "method" in mensagem and "id" in mensagem:
                # O SLS não ganha autoridade para editar/executar nada por pedir ao cliente.
                self.envie({"jsonrpc": "2.0", "id": mensagem["id"],
                            "error": {"code": -32601, "message": "cliente de ensaio não executa pedidos"}})
                raise FalhaLsp("pedido inesperado ao cliente: " + mensagem["method"])
            self.pendentes.append(mensagem)
            if len(self.pendentes) > 1024:
                raise FalhaLsp("excesso de notificações/respostas sem consumo")

    def solicite_bruto(self, metodo, parametros=None):
        self.contador += 1
        identidade = self.contador
        self.envie({"jsonrpc": "2.0", "id": identidade, "method": metodo,
                    "params": parametros if parametros is not None else {}})
        resposta = self.receba(lambda item: item.get("id") == identidade)
        if ("result" in resposta) == ("error" in resposta):
            raise FalhaLsp("resposta precisa conter result ou error, exclusivamente")
        return resposta

    def solicite(self, metodo, parametros=None):
        resposta = self.solicite_bruto(metodo, parametros)
        if "error" in resposta:
            raise FalhaLsp(f"{metodo}: {resposta['error']}")
        return resposta["result"]

    def inicie(self):
        resultado = self.solicite("initialize", {
            "processId": os.getpid(), "rootUri": self.raiz.as_uri(),
            "workspaceFolders": [{"uri": self.raiz.as_uri(), "name": "homologação"}],
            "capabilities": {
                "general": {"positionEncodings": ["utf-16"]},
                "workspace": {"workspaceFolders": True, "workspaceEdit": {"documentChanges": True}},
                "textDocument": {
                    "publishDiagnostics": {"versionSupport": True},
                    "completion": {"completionItem": {"snippetSupport": False}},
                    "rename": {"prepareSupport": True},
                    "codeAction": {"codeActionLiteralSupport": {"codeActionKind": {"valueSet": ["quickfix"]}}},
                    "semanticTokens": {"requests": {"full": True}, "formats": ["relative"],
                        "tokenTypes": ["namespace", "type", "class", "parameter", "variable", "property",
                                       "function", "method", "keyword", "comment", "string", "number", "operator"],
                        "tokenModifiers": ["declaration", "readonly", "defaultLibrary"]},
                },
            },
        })
        self.capacidades = resultado["capabilities"]
        self.informacao = resultado.get("serverInfo", {})
        self.iniciado = True
        self.notifique("initialized")
        return resultado

    def exija(self, capacidade):
        valor = self.capacidades.get(capacidade)
        if valor is None or valor is False:
            raise Pendente("capacidade não anunciada: " + capacidade)
        return valor

    def abra(self, texto, nome="principal.fé"):
        caminho = self.raiz / nome
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(texto, encoding="utf-8")
        uri = caminho.as_uri()
        self.documentos[uri] = (texto, 1)
        self.notifique("textDocument/didOpen", {"textDocument": {
            "uri": uri, "languageId": "santafe", "version": 1, "text": texto}})
        return uri

    def diagnosticos(self, uri, versao=None):
        resposta = self.receba(lambda item: item.get("method") == "textDocument/publishDiagnostics"
                              and item.get("params", {}).get("uri") == uri
                              and (versao is None or item.get("params", {}).get("version") == versao))
        diagnosticos = resposta["params"]["diagnostics"]
        if not isinstance(diagnosticos, list):
            raise FalhaLsp("diagnostics não é uma matriz JSON")
        return diagnosticos

    def mude(self, uri, texto):
        anterior, versao = self.documentos[uri]
        sync = self.capacidades["textDocumentSync"]
        modo = sync.get("change") if isinstance(sync, dict) else sync
        mudanca = {"text": texto}
        if modo == 2:
            mudanca["range"] = {"start": {"line": 0, "character": 0},
                                "end": posicao(anterior, len(anterior))}
        self.notifique("textDocument/didChange", {"textDocument": {"uri": uri, "version": versao + 1},
                                                "contentChanges": [mudanca]})
        self.documentos[uri] = (texto, versao + 1)
        return versao + 1

    def no_ponto(self, uri, texto, trecho, ultimo=False, dentro=0):
        indice = texto.rfind(trecho) if ultimo else texto.find(trecho)
        if indice < 0:
            raise FalhaLsp("marcador de teste inexistente: " + trecho)
        return {"textDocument": {"uri": uri}, "position": posicao(texto, indice + dentro)}

    def feche(self):
        try:
            if self.processo.poll() is None and self.iniciado:
                resposta = self.solicite("shutdown")
                if resposta is not None:
                    raise FalhaLsp("shutdown precisa devolver null")
                self.notifique("exit")
                if self.processo.wait(timeout=self.prazo) != 0:
                    raise FalhaLsp("saída não zero após shutdown/exit")
        finally:
            self.vigia.cancel()
            self._mate()
            self.processo.wait(timeout=5)
            self.leitor.join(timeout=1)
            self.leitor_erros.join(timeout=1)
            for canal in (self.processo.stdin, self.processo.stdout, self.processo.stderr):
                canal.close()
