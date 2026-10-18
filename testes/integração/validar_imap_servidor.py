#!/usr/bin/env python3
"""Valida um processo IMAP já iniciado sem registrar a credencial."""

from __future__ import annotations

import argparse
import imaplib
import os
import re
import ssl


def principal() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--porta", type=int, required=True)
    parser.add_argument("--usuario", required=True)
    parser.add_argument("--senha", default=os.environ.get(
        "SANTAFE_IMAP_TEST_PASSWORD"
    ))
    args = parser.parse_args()
    if not args.senha:
        parser.error("informe --senha ou SANTAFE_IMAP_TEST_PASSWORD")

    contexto = ssl.create_default_context()
    contexto.check_hostname = False
    contexto.verify_mode = ssl.CERT_NONE

    cliente = imaplib.IMAP4_SSL(
        args.host, args.porta, ssl_context=contexto, timeout=8
    )
    capacidades = {
        item.decode("ascii").upper() if isinstance(item, bytes) else str(item).upper()
        for item in cliente.capabilities
    }
    assert "IMAP4REV1" in capacidades
    assert "AUTH=PLAIN" in capacidades
    assert "UIDPLUS" in capacidades
    assert "LIST-EXTENDED" in capacidades
    assert "SPECIAL-USE" in capacidades

    try:
        cliente.login(args.usuario, args.senha + "-incorreta")
        raise AssertionError("senha incorreta foi aceita")
    except imaplib.IMAP4.error:
        pass

    tipo, _ = cliente.authenticate(
        "PLAIN",
        lambda _: b"\0" + args.usuario.encode() + b"\0" + args.senha.encode(),
    )
    assert tipo == "OK"
    tipo, caixas = cliente.list()
    assert tipo == "OK"
    listagem = b"\n".join(caixas)
    for nome in (
        b"INBOX", b"Enviadas", b"Rascunhos", b"Arquivadas",
        b"Indesejadas", b"Lixeira",
    ):
        assert nome in listagem

    tipo, dados = cliente._simple_command("LIST", '""', '""')
    tipo, raiz_da_lista = cliente._untagged_response(tipo, dados, "LIST")
    assert tipo == "OK"
    raiz_bruta = b"\n".join(raiz_da_lista)
    assert b"\\Noselect" in raiz_bruta and b"Enviadas" not in raiz_bruta

    tipo, dados = cliente._simple_command(
        "LIST", "(SPECIAL-USE)", '""', '"*"'
    )
    tipo, especiais = cliente._untagged_response(tipo, dados, "LIST")
    assert tipo == "OK"
    especiais_brutas = b"\n".join(especiais)
    assert b"INBOX" not in especiais_brutas
    for marcador in (
        b"\\Sent", b"\\Drafts", b"\\Archive", b"\\Junk", b"\\Trash",
    ):
        assert marcador in especiais_brutas

    tipo, uma_caixa = cliente.list('""', '"INBOX"')
    assert tipo == "OK" and len(uma_caixa) == 1
    assert b"\\Inbox" not in uma_caixa[0]
    tipo, quantidade = cliente.select("INBOX")
    assert tipo == "OK" and quantidade == [b"0"]
    tipo, quantidade = cliente.select("Lixeira")
    assert tipo == "OK"
    tipo, uids_anteriores = cliente.uid("SEARCH", None, "ALL")
    assert tipo == "OK"
    uids_anteriores = set(uids_anteriores[0].split())
    tipo, quantidade = cliente.select("INBOX")
    assert tipo == "OK" and quantidade == [b"0"]

    mime = (
        f"From: {args.usuario}\r\n"
        "To: ana@example.net\r\n"
        "Subject: Ensaio APPEND instalado\r\n"
        f"Message-ID: <append-{args.usuario}>\r\n"
        "Content-Type: text/plain; charset=UTF-8\r\n\r\n"
        "Rascunho UTF-8 preservado pelo Correio Santafé."
    ).encode("utf-8")
    tipo, resposta = cliente.append(
        "Rascunhos", "(\\Seen \\Draft)",
        '"31-Aug-2026 02:03:04 +0000"', mime,
    )
    resposta_append = b" ".join(resposta)
    correspondência_uid = re.search(
        rb"APPENDUID\s+\d+\s+(\d+)", resposta_append
    )
    assert tipo == "OK" and correspondência_uid is not None
    uid_rascunho = correspondência_uid.group(1).decode("ascii")
    tipo, quantidade = cliente.select("Rascunhos")
    assert tipo == "OK" and quantidade == [b"1"]
    tipo, dados = cliente.fetch("1", "(FLAGS INTERNALDATE BODY.PEEK[])")
    bruto = repr(dados).encode()
    assert tipo == "OK" and b"Ensaio APPEND instalado" in bruto
    assert b"31-Aug-2026 02:03:04 +0000" in bruto
    tipo, dados = cliente.uid(
        "FETCH", uid_rascunho, "(BODY.PEEK[] BODYSTRUCTURE)"
    )
    bruto_uid = repr(dados).encode()
    assert tipo == "OK"
    assert f"UID {uid_rascunho}".encode("ascii") in bruto_uid
    assert b"Ensaio APPEND instalado" in bruto_uid
    tipo, dados = cliente.uid(
        "FETCH", uid_rascunho,
        "(UID BODY.PEEK[1.MIME] BODY.PEEK[1]<0.65536>)",
    )
    apple_bruto = repr(dados).encode()
    assert tipo == "OK"
    assert b"Content-Transfer-Encoding: 8bit" in apple_bruto
    assert b"Rascunho UTF-8 preservado" in apple_bruto

    tipo, _ = cliente.uid("COPY", uid_rascunho, "Arquivadas")
    nome_do_código, resposta_da_cópia = cliente.response("COPYUID")
    resposta_da_cópia_bruta = b" ".join(resposta_da_cópia or [])
    assert tipo == "OK"
    assert nome_do_código == "COPYUID"
    correspondência_da_cópia = re.search(
        rb"(\d+)\s+" + uid_rascunho.encode("ascii") +
        rb"\s+(\d+)", resposta_da_cópia_bruta,
    )
    assert correspondência_da_cópia is not None
    uid_copiado = correspondência_da_cópia.group(2).decode("ascii")
    tipo, quantidade = cliente.select("Rascunhos")
    assert tipo == "OK" and quantidade == [b"1"]
    tipo, quantidade = cliente.select("Arquivadas")
    assert tipo == "OK" and quantidade == [b"1"]
    tipo, dados_copiados = cliente.uid(
        "FETCH", uid_copiado, "(UID FLAGS INTERNALDATE BODY.PEEK[])"
    )
    bruto_copiado = repr(dados_copiados).encode()
    assert tipo == "OK" and b"Rascunho UTF-8 preservado" in bruto_copiado
    assert b"\\Seen" in bruto_copiado
    assert b"31-Aug-2026 02:03:04 +0000" in bruto_copiado
    tipo, quantidade = cliente.select("Rascunhos")
    assert tipo == "OK" and quantidade == [b"1"]

    tipo, _ = cliente.uid(
        "STORE", uid_rascunho, "+FLAGS", "(\\Deleted)"
    )
    assert tipo == "OK"

    # Reproduz o Gmail móvel: a marca e o expurgo podem ocorrer em
    # conexões diferentes.
    cliente.logout()
    cliente = imaplib.IMAP4_SSL(
        args.host, args.porta, ssl_context=contexto, timeout=8
    )
    tipo, _ = cliente.authenticate(
        "PLAIN",
        lambda _: b"\0" + args.usuario.encode() + b"\0" + args.senha.encode(),
    )
    assert tipo == "OK"
    tipo, _ = cliente.select("Rascunhos")
    assert tipo == "OK"
    tipo, marcas = cliente.uid("FETCH", uid_rascunho, "(FLAGS)")
    assert tipo == "OK" and b"\\Deleted" in repr(marcas).encode()
    tipo, _ = cliente.uid("EXPUNGE", uid_rascunho)
    assert tipo == "OK"
    tipo, quantidade = cliente.select("Lixeira")
    assert tipo == "OK"
    tipo, uids_atuais = cliente.uid("SEARCH", None, "ALL")
    assert tipo == "OK"
    novos_uids = set(uids_atuais[0].split()) - uids_anteriores
    assert len(novos_uids) == 1
    uid_na_lixeira = novos_uids.pop().decode("ascii")
    tipo, _ = cliente.uid(
        "STORE", uid_na_lixeira, "+FLAGS", "(\\Deleted)"
    )
    assert tipo == "OK"
    cliente.logout()
    cliente = imaplib.IMAP4_SSL(
        args.host, args.porta, ssl_context=contexto, timeout=8
    )
    tipo, _ = cliente.authenticate(
        "PLAIN",
        lambda _: b"\0" + args.usuario.encode() + b"\0" + args.senha.encode(),
    )
    assert tipo == "OK"
    tipo, _ = cliente.select("Lixeira")
    assert tipo == "OK"
    tipo, _ = cliente.uid("EXPUNGE", uid_na_lixeira)
    assert tipo == "OK"

    enviada = mime.replace(b"Rascunho", b"Enviada")
    tipo, primeira = cliente.append("Enviadas", "(\\Seen)", None, enviada)
    assert tipo == "OK" and b"APPENDUID" in b" ".join(primeira)
    tipo, segunda = cliente.append("Enviadas", "(\\Seen)", None, enviada)
    assert tipo == "OK" and primeira == segunda
    tipo, quantidade = cliente.select("Enviadas")
    assert tipo == "OK" and quantidade == [b"1"]
    cliente.logout()
    print("Correio IMAP instalado, TLS, AUTH, COPY, Arquivadas, APPEND, UIDPLUS e Lixeira: ok")


if __name__ == "__main__":
    principal()
