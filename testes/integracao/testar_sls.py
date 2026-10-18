#!/usr/bin/env python3
"""Ensaio de ponta a ponta do Servidor de Linguagem Santafé (SLS)."""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import threading


RAIZ = pathlib.Path(__file__).resolve().parents[2]
INTERPRETADOR = RAIZ / "src" / "santafé"
SERVIDOR = RAIZ / "ferramentas" / "sls" / "sls.fé"


def envie(processo: subprocess.Popen[bytes], mensagem: dict) -> None:
    conteúdo = json.dumps(mensagem, ensure_ascii=False, separators=(",", ":")).encode()
    processo.stdin.write(
        f"Content-Length: {len(conteúdo)}\r\n\r\n".encode() + conteúdo
    )
    processo.stdin.flush()


def leia(processo: subprocess.Popen[bytes]) -> dict:
    cabeçalhos: dict[bytes, bytes] = {}
    while True:
        linha = processo.stdout.readline()
        assert linha, "SLS fechou a saída antes da resposta"
        if linha in (b"\r\n", b"\n"):
            break
        nome, valor = linha.rstrip(b"\r\n").split(b":", 1)
        cabeçalhos[nome.lower()] = valor.strip()

    tamanho = int(cabeçalhos[b"content-length"])
    conteúdo = processo.stdout.read(tamanho)
    assert len(conteúdo) == tamanho, "quadro LSP truncado"
    return json.loads(conteúdo)


def principal() -> None:
    assert INTERPRETADOR.is_file(), "compile o núcleo antes de testar o SLS"

    processo = subprocess.Popen(
        [str(INTERPRETADOR), str(SERVIDOR)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert processo.stdin and processo.stdout
    prazo = threading.Timer(15, processo.kill)
    prazo.start()

    uri = "file:///tmp/exemplo-sls.fé"
    try:
        envie(processo, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        inicialização = leia(processo)
        assert inicialização["id"] == 1
        capacidades = inicialização["result"]["capabilities"]
        assert capacidades["textDocumentSync"]["change"] == 1
        assert capacidades["positionEncoding"] == "utf-16"

        envie(processo, {
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {"textDocument": {"uri": uri, "version": 1, "text": "mostre(42)\n"}},
        })
        limpo = leia(processo)
        assert limpo["method"] == "textDocument/publishDiagnostics"
        assert limpo["params"]["uri"] == uri
        assert limpo["params"]["diagnostics"] == [], limpo

        envie(processo, {
            "jsonrpc": "2.0",
            "method": "textDocument/didChange",
            "params": {
                "textDocument": {"uri": uri, "version": 2},
                "contentChanges": [{"text": "se verdadeiro então\n"}],
            },
        })
        inválido = leia(processo)
        diagnóstico = inválido["params"]["diagnostics"][0]
        assert diagnóstico["source"] == "SLS"
        assert diagnóstico["severity"] == 1
        assert diagnóstico["range"]["start"]["line"] == 1

        envie(processo, {
            "jsonrpc": "2.0",
            "method": "textDocument/didClose",
            "params": {"textDocument": {"uri": uri}},
        })
        fechado = leia(processo)
        assert fechado["params"]["diagnostics"] == []

        envie(processo, {"jsonrpc": "2.0", "id": 2, "method": "shutdown", "params": {}})
        encerramento = leia(processo)
        assert encerramento == {"jsonrpc": "2.0", "id": 2, "result": None}
        envie(processo, {"jsonrpc": "2.0", "method": "exit", "params": {}})

        assert processo.wait(timeout=5) == 0
    finally:
        prazo.cancel()
        if processo.poll() is None:
            processo.kill()
        processo.wait(timeout=5)

    print("SLS LSP, sincronização e diagnósticos: ok")


if __name__ == "__main__":
    try:
        principal()
    except (AssertionError, OSError, ValueError, json.JSONDecodeError) as erro:
        print(f"FALHA SLS: {erro}", file=sys.stderr)
        raise SystemExit(1)
