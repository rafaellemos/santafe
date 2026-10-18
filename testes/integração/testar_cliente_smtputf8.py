#!/usr/bin/env python3

"""Envia uma carta EAI real pela Agência SMTP do Correio Santafé."""

import argparse
import getpass
import smtplib
import ssl
import sys
from email import policy
from email.message import EmailMessage


def leia_argumentos():
    parser = argparse.ArgumentParser(
        description="Homologa SMTPUTF8 pela porta de submissão STARTTLS."
    )
    parser.add_argument("--servidor", default="xn--santaf-gva.dev.br")
    parser.add_argument("--porta", type=int, default=587)
    parser.add_argument("--usuario", default="rafael")
    parser.add_argument(
        "--remetente-envelope",
        default="rafael@xn--santaf-gva.dev.br",
    )
    parser.add_argument(
        "--remetente-cabecalho",
        default="rafael@santafé.dev.br",
    )
    parser.add_argument(
        "--destinatario",
        default="josé@santafé.dev.br",
    )
    parser.add_argument(
        "--mostrar-protocolo",
        action="store_true",
        help="mostra MAIL, RCPT e DATA; a autenticação permanece oculta",
    )
    return parser.parse_args()


def execute(opcoes):
    senha = getpass.getpass(f"Senha SMTP de {opcoes.usuario}: ")

    mensagem = EmailMessage(policy=policy.SMTPUTF8)
    mensagem["Subject"] = "Teste de homologação EAI — Correio Santafé"
    mensagem["From"] = opcoes.remetente_cabecalho
    mensagem["To"] = opcoes.destinatario
    mensagem.set_content(
        "Corpo da mensagem de teste com acentuação: ã, é, ç.\n"
    )

    contexto_tls = ssl.create_default_context()
    print(f"[*] Conectando a {opcoes.servidor}:{opcoes.porta}...")

    with smtplib.SMTP(
        opcoes.servidor,
        opcoes.porta,
        timeout=20,
    ) as cliente:
        codigo, _ = cliente.ehlo()
        if codigo != 250:
            raise RuntimeError(f"EHLO recusado antes do TLS: {codigo}")
        if not cliente.has_extn("starttls"):
            raise RuntimeError("o servidor não anunciou STARTTLS")

        print("[+] STARTTLS anunciado. Iniciando TLS...")
        cliente.starttls(context=contexto_tls)

        codigo, _ = cliente.ehlo()
        if codigo != 250:
            raise RuntimeError(f"EHLO recusado depois do TLS: {codigo}")
        if not cliente.has_extn("smtputf8"):
            raise RuntimeError("o servidor não anunciou SMTPUTF8")
        if not cliente.has_extn("8bitmime"):
            raise RuntimeError("o servidor não anunciou 8BITMIME")

        print("[+] SMTPUTF8 e 8BITMIME confirmados.")
        print("[*] Autenticando...")
        cliente.login(opcoes.usuario, senha)

        # A depuração só começa depois do AUTH para não expor a senha.
        if opcoes.mostrar_protocolo:
            cliente.set_debuglevel(1)

        recusados = cliente.send_message(
            mensagem,
            from_addr=opcoes.remetente_envelope,
            to_addrs=[opcoes.destinatario],
        )
        cliente.set_debuglevel(0)

        if recusados:
            raise RuntimeError(f"destinatários recusados: {recusados}")

    print("[+] Mensagem EAI enviada com sucesso.")
    print(f"[+] Destinatário preservado: {opcoes.destinatario}")


def principal():
    try:
        execute(leia_argumentos())
    except (smtplib.SMTPException, OSError, RuntimeError) as erro:
        print(f"[-] Falha no teste: {erro}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
