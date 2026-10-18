#!/usr/bin/env python3

"""Valida SMTPUTF8 sem transmitir DATA nem persistir uma carta."""

import argparse
import socket


def leia_resposta(conexao):
    linhas = []
    while True:
        linha = b""
        while not linha.endswith(b"\n"):
            parte = conexao.recv(1)
            if not parte:
                raise RuntimeError("o servidor encerrou a conexão durante a resposta")
            linha += parte
        linhas.append(linha)
        if len(linha) < 4 or linha[3:4] != b"-":
            return linhas


def exija_codigo(linhas, codigo, etapa):
    recebido = linhas[-1][:3]
    esperado = str(codigo).encode("ascii")
    if recebido != esperado:
        texto = b"".join(linhas).decode("utf-8", "replace").strip()
        raise RuntimeError(f"{etapa}: esperado {codigo}, recebido {texto}")


def envie(conexao, comando, codigo, etapa):
    conexao.sendall(comando + b"\r\n")
    resposta = leia_resposta(conexao)
    exija_codigo(resposta, codigo, etapa)
    return resposta


def principal():
    argumentos = argparse.ArgumentParser()
    argumentos.add_argument("--endereco", default="127.0.0.1")
    argumentos.add_argument("--porta", type=int, default=25)
    argumentos.add_argument("--destinatario", required=True)
    opcoes = argumentos.parse_args()

    with socket.create_connection((opcoes.endereco, opcoes.porta), timeout=5) as conexao:
        conexao.settimeout(5)
        exija_codigo(leia_resposta(conexao), 220, "saudação")
        capacidades = envie(conexao, b"EHLO auditoria.local", 250, "EHLO")
        if b"SMTPUTF8" not in b"".join(capacidades).upper():
            raise RuntimeError("o servidor não anunciou SMTPUTF8")
        envie(
            conexao,
            b"MAIL FROM:<auditoria@exemplo.net> SMTPUTF8",
            250,
            "MAIL FROM",
        )
        destino = f"RCPT TO:<{opcoes.destinatario}>".encode("utf-8")
        envie(conexao, destino, 250, "RCPT TO SMTPUTF8")
        envie(conexao, b"RSET", 250, "RSET")
        envie(conexao, b"QUIT", 221, "QUIT")

    print("SMTPUTF8 exato: ok")


if __name__ == "__main__":
    principal()
