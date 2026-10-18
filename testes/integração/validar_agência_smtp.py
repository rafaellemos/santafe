#!/usr/bin/env python3
"""Valida TLS, STARTTLS e a política AUTH da Correio Agência."""

import argparse
import base64
import socket
import ssl


def resposta(arquivo):
    primeira = arquivo.readline()
    if not primeira:
        raise RuntimeError("servidor SMTP encerrou a conexão")
    texto = primeira.decode("utf-8", "replace").rstrip("\r\n")
    if len(texto) < 3 or not texto[:3].isdigit():
        raise RuntimeError(f"resposta SMTP inválida: {texto!r}")
    código = int(texto[:3])
    linhas = [texto]
    while len(texto) >= 4 and texto[3] == "-":
        próxima = arquivo.readline()
        if not próxima:
            raise RuntimeError("resposta SMTP multilinha incompleta")
        texto = próxima.decode("utf-8", "replace").rstrip("\r\n")
        linhas.append(texto)
        if texto.startswith(f"{código} "):
            break
    return código, linhas


def envie(sock, arquivo, comando, esperado):
    sock.sendall((comando + "\r\n").encode("ascii"))
    código, linhas = resposta(arquivo)
    if código not in esperado:
        raise RuntimeError(
            f"{comando.split(' ', 1)[0]} devolveu {código}: " +
            " | ".join(linhas)
        )
    return linhas


def capacidades(linhas):
    return "\n".join(linhas).upper()


def valide_início_tls(host, porta, nome, contexto, tempo):
    bruto = socket.create_connection((host, porta), timeout=tempo)
    bruto.settimeout(tempo)
    arquivo = bruto.makefile("rb")
    código, _ = resposta(arquivo)
    if código != 220:
        raise RuntimeError(f"saudação STARTTLS devolveu {código}")
    antes = capacidades(envie(bruto, arquivo, "EHLO ensaio.local", {250}))
    if "STARTTLS" not in antes:
        raise RuntimeError("porta 587 não anunciou STARTTLS")
    if "AUTH PLAIN" in antes:
        raise RuntimeError("porta 587 anunciou AUTH antes da criptografia")
    envie(bruto, arquivo, "STARTTLS", {220})
    arquivo.close()
    seguro = contexto.wrap_socket(bruto, server_hostname=nome)
    seguro.settimeout(tempo)
    arquivo = seguro.makefile("rb")
    depois = capacidades(envie(seguro, arquivo, "EHLO ensaio.local", {250}))
    if "AUTH PLAIN" not in depois:
        raise RuntimeError("porta 587 não anunciou AUTH após STARTTLS")
    envie(seguro, arquivo, "QUIT", {221})
    arquivo.close()
    seguro.close()


def valide_tls(host, porta, nome, contexto, tempo):
    bruto = socket.create_connection((host, porta), timeout=tempo)
    seguro = contexto.wrap_socket(bruto, server_hostname=nome)
    seguro.settimeout(tempo)
    arquivo = seguro.makefile("rb")
    código, _ = resposta(arquivo)
    if código != 220:
        raise RuntimeError(f"saudação TLS devolveu {código}")
    anúncio = capacidades(envie(seguro, arquivo, "EHLO ensaio.local", {250}))
    if "AUTH PLAIN" not in anúncio:
        raise RuntimeError("porta 465 não anunciou AUTH PLAIN")
    credencial = base64.b64encode(
        b"\0conta-que-nao-existe\0senha-incorreta"
    ).decode("ascii")
    envie(seguro, arquivo, "AUTH PLAIN " + credencial, {535})
    envie(seguro, arquivo, "QUIT", {221})
    arquivo.close()
    seguro.close()


def principal():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--porta-starttls", type=int, required=True)
    parser.add_argument("--porta-tls", type=int, required=True)
    parser.add_argument("--nome", required=True)
    parser.add_argument("--tempo", type=float, default=20)
    args = parser.parse_args()

    contexto = ssl.create_default_context()
    valide_início_tls(
        args.host, args.porta_starttls, args.nome, contexto, args.tempo
    )
    valide_tls(args.host, args.porta_tls, args.nome, contexto, args.tempo)
    print("Correio Agência TLS, STARTTLS e AUTH: ok")


if __name__ == "__main__":
    principal()
