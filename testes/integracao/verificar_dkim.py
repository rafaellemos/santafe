#!/usr/bin/env python3
"""Verifica, de modo independente, uma assinatura DKIM relaxed/relaxed."""

from __future__ import annotations

import base64
import hashlib
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def falhe(mensagem: str) -> None:
    raise SystemExit(f"ERRO: {mensagem}")


def normalize_quebras(dados: bytes) -> bytes:
    return dados.replace(b"\r\n", b"\n").replace(b"\r", b"\n").replace(
        b"\n", b"\r\n"
    )


def leia_cabecalhos(bloco: bytes) -> list[tuple[bytes, bytes]]:
    resultado: list[tuple[bytes, bytes]] = []
    for linha in bloco.split(b"\r\n"):
        if linha.startswith((b" ", b"\t")):
            if not resultado:
                falhe("continuação antes do primeiro cabeçalho")
            nome, valor = resultado[-1]
            resultado[-1] = nome, valor + b"\r\n" + linha
            continue
        if b":" not in linha:
            falhe("cabeçalho sem dois-pontos")
        nome, valor = linha.split(b":", 1)
        resultado.append((nome, valor))
    return resultado


def cabecalho_relaxado(nome: bytes, valor: bytes) -> bytes:
    valor = re.sub(br"\r\n[ \t]+", b" ", valor)
    valor = re.sub(br"[ \t]+", b" ", valor).strip(b" \t")
    return nome.lower() + b":" + valor


def corpo_relaxado(corpo: bytes) -> bytes:
    linhas = [re.sub(br"[ \t]+", b" ", linha.rstrip(b" \t"))
              for linha in corpo.split(b"\r\n")]
    while linhas and linhas[-1] == b"":
        linhas.pop()
    return b"\r\n" if not linhas else b"\r\n".join(linhas) + b"\r\n"


def principal() -> None:
    if len(sys.argv) != 3:
        falhe("uso: verificar_dkim.py mensagem.eml chave-privada.pem")
    mensagem = normalize_quebras(Path(sys.argv[1]).read_bytes())
    separador = mensagem.find(b"\r\n\r\n")
    if separador < 0:
        falhe("mensagem sem separador de corpo")
    cabecalhos = leia_cabecalhos(mensagem[:separador])
    corpo = mensagem[separador + 4 :]
    dkim = next(((n, v) for n, v in cabecalhos if n.lower() == b"dkim-signature"), None)
    if not dkim:
        falhe("DKIM-Signature ausente")

    valor_dkim = re.sub(br"\r\n[ \t]+", b" ", dkim[1]).strip()
    etiquetas = {}
    for parte in valor_dkim.split(b";"):
        if b"=" in parte:
            chave, valor = parte.strip().split(b"=", 1)
            etiquetas[chave] = valor
    for obrigatoria in (b"a", b"c", b"d", b"s", b"h", b"bh", b"b"):
        if obrigatoria not in etiquetas:
            falhe(f"etiqueta DKIM ausente: {obrigatoria.decode()}")
    if etiquetas[b"a"] != b"rsa-sha256" or etiquetas[b"c"] != b"relaxed/relaxed":
        falhe("algoritmo ou canonicalização inesperados")

    resumo = base64.b64encode(hashlib.sha256(corpo_relaxado(corpo)).digest())
    if resumo != etiquetas[b"bh"]:
        falhe("resumo do corpo não confere")

    escolhidos = []
    usados: set[int] = set()
    for desejado in etiquetas[b"h"].lower().split(b":"):
        for indice in range(len(cabecalhos) - 1, -1, -1):
            nome, valor = cabecalhos[indice]
            if indice not in usados and nome.lower() == desejado:
                usados.add(indice)
                escolhidos.append(cabecalho_relaxado(nome, valor) + b"\r\n")
                break
        else:
            falhe(f"cabeçalho assinado ausente: {desejado.decode()}")

    valor_sem_assinatura = re.sub(br"\bb=[^;]*$", b"b=", valor_dkim)
    dados_assinados = b"".join(escolhidos) + cabecalho_relaxado(
        b"DKIM-Signature", b" " + valor_sem_assinatura
    )
    assinatura = base64.b64decode(etiquetas[b"b"], validate=True)

    publica = subprocess.run(
        ["openssl", "pkey", "-in", sys.argv[2], "-pubout"],
        check=True, capture_output=True,
    ).stdout
    with tempfile.TemporaryDirectory(prefix="santafe-dkim-") as pasta:
        pasta = Path(pasta)
        (pasta / "publica.pem").write_bytes(publica)
        (pasta / "assinatura.bin").write_bytes(assinatura)
        verificacao = subprocess.run(
            ["openssl", "dgst", "-sha256", "-verify", str(pasta / "publica.pem"),
             "-signature", str(pasta / "assinatura.bin")],
            input=dados_assinados, capture_output=True,
        )
    if verificacao.returncode != 0:
        falhe(verificacao.stderr.decode(errors="replace") or "assinatura RSA inválida")
    print("DKIM independente: ok")


if __name__ == "__main__":
    principal()
