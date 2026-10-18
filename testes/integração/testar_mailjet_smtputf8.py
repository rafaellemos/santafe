#!/usr/bin/env python3

"""Comprova SMTPUTF8 no retransmissor Mailjet sem expor credenciais."""

import argparse
import getpass
import os
import smtplib
import ssl
import sys
from email import policy
from email.message import EmailMessage


def leia_argumentos():
    analisador = argparse.ArgumentParser(
        description="Envia uma carta EAI real pelo SMTP do Mailjet."
    )
    analisador.add_argument("--servidor", default="in-v3.mailjet.com")
    analisador.add_argument("--porta", type=int, default=587)
    analisador.add_argument(
        "--usuario",
        default=(
            os.environ.get("MAILJET_SMTP_USUARIO")
            or os.environ.get("CORREIO_ENVIOS_USUARIO")
        ),
        help="chave de API usada como usuário SMTP",
    )
    analisador.add_argument("--remetente")
    analisador.add_argument("--destinatario")
    analisador.add_argument("--nome", default="Correio Santafé")
    analisador.add_argument("--mostrar-protocolo", action="store_true")
    analisador.add_argument(
        "--somente-autenticacao",
        action="store_true",
        help="valida TLS, capacidades e credenciais sem enviar carta",
    )
    return analisador.parse_args()


def execute(opcoes):
    if not opcoes.usuario:
        raise RuntimeError(
            "informe --usuario, MAILJET_SMTP_USUARIO ou CORREIO_ENVIOS_USUARIO"
        )
    segredo = (
        os.environ.get("MAILJET_SMTP_SENHA")
        or os.environ.get("CORREIO_ENVIOS_SENHA")
    )
    if segredo is None:
        segredo = getpass.getpass("Chave secreta SMTP do Mailjet: ")
    if not segredo:
        raise RuntimeError("a chave secreta SMTP está vazia")
    if not opcoes.somente_autenticacao and (
        not opcoes.remetente or not opcoes.destinatario
    ):
        raise RuntimeError(
            "informe remetente e destinatário ou use --somente-autenticacao"
        )

    contexto = ssl.create_default_context()
    with smtplib.SMTP(opcoes.servidor, opcoes.porta, timeout=30) as cliente:
        codigo, _ = cliente.ehlo()
        if codigo != 250 or not cliente.has_extn("starttls"):
            raise RuntimeError("o Mailjet não anunciou STARTTLS")

        cliente.starttls(context=contexto)
        codigo, _ = cliente.ehlo()
        if codigo != 250:
            raise RuntimeError(f"EHLO recusado depois do TLS: {codigo}")
        if not cliente.has_extn("smtputf8"):
            raise RuntimeError("o retransmissor não anunciou SMTPUTF8")
        if not cliente.has_extn("8bitmime"):
            raise RuntimeError("o retransmissor não anunciou 8BITMIME")

        cliente.login(opcoes.usuario, segredo)
        if opcoes.somente_autenticacao:
            print("MAILJET_AUTENTICACAO_OK")
            print("SMTPUTF8 e 8BITMIME anunciados sob STARTTLS.")
            return

        mensagem = EmailMessage(policy=policy.SMTPUTF8)
        mensagem["Subject"] = "Homologação SMTPUTF8 — Correio Santafé"
        mensagem["From"] = f"{opcoes.nome} <{opcoes.remetente}>"
        mensagem["To"] = opcoes.destinatario
        mensagem.set_content(
            "Carta de homologação do retransmissor com endereços Unicode.\n",
            cte="8bit",
        )
        if opcoes.mostrar_protocolo:
            cliente.set_debuglevel(1)

        recusados = cliente.send_message(
            mensagem,
            from_addr=opcoes.remetente,
            to_addrs=[opcoes.destinatario],
            mail_options=["SMTPUTF8", "BODY=8BITMIME"],
        )
        cliente.set_debuglevel(0)
        if recusados:
            raise RuntimeError(f"destinatários recusados: {recusados}")

    print("MAILJET_SMTPUTF8_OK")
    print(f"Remetente preservado: {opcoes.remetente}")
    print(f"Destinatário preservado: {opcoes.destinatario}")


def principal():
    try:
        execute(leia_argumentos())
    except (OSError, RuntimeError, smtplib.SMTPException) as erro:
        print(f"MAILJET_SMTPUTF8_FALHOU: {erro}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
