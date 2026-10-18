#!/usr/bin/env python3
"""Valida o subconjunto IMAP do Correio contra a biblioteca padrão Python."""

from __future__ import annotations

import argparse
import base64
import imaplib
import os
import signal
import socket
import ssl
import subprocess
import sys
import time
from pathlib import Path


def leia_ate_etiqueta(arquivo, etiqueta: bytes) -> bytes:
    linhas: list[bytes] = []
    while True:
        linha = arquivo.readline()
        if not linha:
            raise RuntimeError(f"conexão encerrada antes de {etiqueta!r}")
        linhas.append(linha)
        if linha.startswith(etiqueta + b" "):
            return b"".join(linhas)


def garanta_controle_ascii(dados: bytes) -> None:
    estranhos = [valor for valor in dados if valor > 0x7F]
    assert not estranhos, f"resposta de controle IMAP não ASCII: {dados!r}"


def anexe_literal(
    cliente: imaplib.IMAP4_SSL,
    etiqueta: bytes,
    pasta: str,
    mensagem: bytes,
    *,
    internacional: bool,
    sinalizadores: str | None = None,
    data_interna: str | None = None,
) -> bytes:
    """Envia APPEND comum ou o literal8 exato definido pelo RFC 6855."""
    partes = [etiqueta, b"APPEND", pasta.encode("ascii")]
    if sinalizadores:
        partes.append(sinalizadores.encode("ascii"))
    if data_interna:
        partes.append(b'"' + data_interna.encode("ascii") + b'"')
    if internacional:
        partes.append(b"UTF8 (~{" + str(len(mensagem)).encode("ascii") + b"}")
    else:
        partes.append(b"{" + str(len(mensagem)).encode("ascii") + b"}")
    cliente.send(b" ".join(partes) + b"\r\n")
    primeira = cliente.readline()
    garanta_controle_ascii(primeira)
    if not primeira.startswith(b"+ "):
        assert primeira.startswith(etiqueta + b" "), primeira
        return primeira
    cliente.send(mensagem + (b")\r\n" if internacional else b"\r\n"))
    resposta = leia_ate_etiqueta(cliente, etiqueta)
    garanta_controle_ascii(
        b"\r\n".join(
            linha for linha in resposta.split(b"\r\n")
            if not linha.startswith(b"*")
        )
    )
    return resposta


def aguarde_porta(porta: int, processo: subprocess.Popen[bytes]) -> None:
    limite = time.monotonic() + 8
    while time.monotonic() < limite:
        if processo.poll() is not None:
            saida = processo.stdout.read().decode("utf-8", "replace")
            raise RuntimeError(f"servidor IMAP encerrou antes do teste:\n{saida}")
        try:
            with socket.create_connection(("127.0.0.1", porta), timeout=0.2):
                return
        except OSError:
            time.sleep(0.05)
    raise RuntimeError("servidor IMAP não abriu a porta de ensaio")


def principal() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--santafe", default="src/santafé")
    parser.add_argument("--porta", type=int, default=19993)
    args = parser.parse_args()

    raiz = Path(__file__).resolve().parents[2]
    ambiente = os.environ.copy()
    ambiente["CORREIO_IMAP_TESTE_PORTA"] = str(args.porta)
    processo = subprocess.Popen(
        [str(raiz / args.santafe),
         str(raiz / "testes/integração/servidor_imap_memória.fé")],
        cwd=raiz,
        env=ambiente,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        aguarde_porta(args.porta, processo)
        contexto = ssl.create_default_context()
        contexto.check_hostname = False
        contexto.verify_mode = ssl.CERT_NONE

        # O Mail do iOS usa pipelining e consulta novamente as capacidades
        # depois da autenticação. Reproduzimos esse diálogo sem incluir
        # literais de cartas para exigir US-ASCII nas linhas de controle.
        bruto_apple = socket.create_connection(("127.0.0.1", args.porta), timeout=4)
        apple = contexto.wrap_socket(bruto_apple, server_hostname="imap.teste")
        arquivo_apple = apple.makefile("rb")
        saudação_apple = arquivo_apple.readline()
        garanta_controle_ascii(saudação_apple)
        credencial = base64.b64encode(
            b"\0teste@xn--santaf-gva.dev.br\0segredo"
        )
        apple.sendall(
            b"P001 AUTHENTICATE PLAIN " + credencial + b"\r\n"
            b"P002 CAPABILITY\r\n"
            b'P003 ID ("name" "Ensaio Apple")\r\n'
        )
        resposta_auth = leia_ate_etiqueta(arquivo_apple, b"P001")
        resposta_capability = leia_ate_etiqueta(arquivo_apple, b"P002")
        resposta_id = leia_ate_etiqueta(arquivo_apple, b"P003")
        garanta_controle_ascii(resposta_auth)
        garanta_controle_ascii(resposta_capability)
        garanta_controle_ascii(resposta_id)
        assert b"[CAPABILITY IMAP4rev1 ID " in resposta_auth
        assert b"AUTH=PLAIN" not in resposta_auth
        assert b"SASL-IR" not in resposta_capability
        assert b" ID " in resposta_capability
        assert b" UNSELECT" in resposta_capability
        assert b" ENABLE" in resposta_capability
        assert b" UTF8=ACCEPT" in resposta_capability
        assert b'"Correio Santafe"' in resposta_id
        apple.sendall(b"P004 ENABLE UTF8=ACCEPT\r\n")
        resposta_enable = leia_ate_etiqueta(arquivo_apple, b"P004")
        garanta_controle_ascii(resposta_enable)
        assert b"* ENABLED UTF8=ACCEPT\r\n" in resposta_enable
        arquivo_apple.close()
        apple.close()

        cliente = imaplib.IMAP4_SSL("127.0.0.1", args.porta, ssl_context=contexto)

        capacidades = {
            (item.decode("ascii") if isinstance(item, bytes) else str(item)).upper()
            for item in cliente.capabilities
        }
        assert "IMAP4REV1" in capacidades
        assert "SPECIAL-USE" in capacidades
        assert "UIDPLUS" in capacidades
        assert "SASL-IR" in capacidades
        assert "ID" in capacidades
        assert "UNSELECT" in capacidades
        assert "ENABLE" in capacidades
        assert "UTF8=ACCEPT" in capacidades

        cliente_auth = imaplib.IMAP4_SSL(
            "127.0.0.1", args.porta, ssl_context=contexto
        )
        tipo, _ = cliente_auth.authenticate(
            "PLAIN", lambda _: b"\0teste@xn--santaf-gva.dev.br\0segredo"
        )
        assert tipo == "OK"
        cliente_auth.logout()

        # Usuário Unicode pertence ao SASL AUTHENTICATE, não ao LOGIN.
        cliente_unicode = imaplib.IMAP4_SSL(
            "127.0.0.1", args.porta, ssl_context=contexto
        )
        tipo, _ = cliente_unicode.authenticate(
            "PLAIN", lambda _: "\0tésté@santafé.dev.br\0segredo".encode("utf-8")
        )
        assert tipo == "OK"
        cliente_unicode.logout()

        bruto_login = socket.create_connection(
            ("127.0.0.1", args.porta), timeout=4
        )
        login_unicode = contexto.wrap_socket(
            bruto_login, server_hostname="imap.teste"
        )
        arquivo_login = login_unicode.makefile("rb")
        arquivo_login.readline()
        login_unicode.sendall(
            'U001 LOGIN "tésté@santafé.dev.br" "segredo"\r\n'.encode("utf-8")
        )
        resposta_login = leia_ate_etiqueta(arquivo_login, b"U001")
        garanta_controle_ascii(resposta_login)
        assert b" NO [CANNOT] " in resposta_login
        arquivo_login.close()
        login_unicode.close()

        try:
            cliente.login("teste@xn--santaf-gva.dev.br", "incorreta")
            raise AssertionError("senha incorreta foi aceita")
        except imaplib.IMAP4.error:
            pass

        tipo, _ = cliente.login("teste@xn--santaf-gva.dev.br", "segredo")
        assert tipo == "OK"

        tipo, capacidades_pós_auth = cliente.capability()
        assert tipo == "OK"
        capacidades_autenticadas = b" ".join(capacidades_pós_auth).upper()
        assert b"AUTH=PLAIN" not in capacidades_autenticadas
        assert b"SASL-IR" not in capacidades_autenticadas
        assert b" ID " in b" " + capacidades_autenticadas + b" "
        assert b" ENABLE " in b" " + capacidades_autenticadas + b" "
        assert b" UTF8=ACCEPT " in b" " + capacidades_autenticadas + b" "

        # O Gmail usa IMAP padrão: autentica e seleciona sem enviar ENABLE.
        gmail = imaplib.IMAP4_SSL(
            "127.0.0.1", args.porta, ssl_context=contexto
        )
        tipo, _ = gmail.login("teste@xn--santaf-gva.dev.br", "segredo")
        assert tipo == "OK"
        tipo, quantidade_gmail = gmail.select("INBOX")
        assert tipo == "OK" and quantidade_gmail == [b"2"]
        gmail.logout()

        tipo, habilitada = cliente.enable("UTF8=ACCEPT")
        assert tipo == "OK"
        assert cliente.utf8_enabled

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
        assert b"\\Noselect" in raiz_bruta and b'""' in raiz_bruta
        assert b"Enviadas" not in raiz_bruta

        # Aspas explícitas preservam o argumento de referência vazio;
        # imaplib omite um colar Python vazio ao montar o comando.
        tipo, uma_caixa = cliente.list('""', '"INBOX"')
        assert tipo == "OK" and len(uma_caixa) == 1
        assert b"INBOX" in uma_caixa[0] and b"\\Inbox" not in uma_caixa[0]

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

        tipo, dados = cliente._simple_command(
            "LIST", '""', '"*"', "RETURN", "(SPECIAL-USE)"
        )
        tipo, lista_com_retorno = cliente._untagged_response(
            tipo, dados, "LIST"
        )
        assert tipo == "OK"
        lista_com_retorno_bruta = b"\n".join(lista_com_retorno)
        assert b"INBOX" in lista_com_retorno_bruta
        assert b"\\Sent" in lista_com_retorno_bruta

        tipo, estado = cliente.status(
            "INBOX", "(MESSAGES UNSEEN UIDNEXT UIDVALIDITY)"
        )
        assert tipo == "OK"
        estado_bruto = b" ".join(estado)
        assert b"MESSAGES 2" in estado_bruto
        assert b"UNSEEN 2" in estado_bruto
        assert b"UIDNEXT 15" in estado_bruto

        tipo, quantidade = cliente.select("INBOX")
        assert tipo == "OK" and quantidade == [b"2"]

        tipo, encontrados = cliente.search(None, "ALL")
        assert tipo == "OK" and encontrados == [b"1 2"]

        cliente.send(b"SFSC SEARCH CHARSET UTF-8 ALL\r\n")
        busca_com_charset = leia_ate_etiqueta(cliente, b"SFSC")
        garanta_controle_ascii(busca_com_charset)
        assert b"SFSC BAD " in busca_com_charset

        tipo, dados = cliente.fetch(
            "1",
            "(UID FLAGS RFC822.SIZE ENVELOPE BODYSTRUCTURE "
            "BODY.PEEK[HEADER.FIELDS (FROM SUBJECT)] BODY.PEEK[TEXT])",
        )
        assert tipo == "OK"
        bruto = repr(dados).encode()
        assert b"Primeira carta" in bruto and b"Ol\\xc3\\xa1 pelo IMAP" in bruto

        tipo, parcial = cliente.fetch("1", "(BODY.PEEK[TEXT]<0.5>)")
        assert tipo == "OK"
        parcial_bruto = repr(parcial).encode()
        assert b"BODY[TEXT]<0>" in parcial_bruto
        assert b"Ol\\xc3\\xa1 " in parcial_bruto

        tipo, corpo_apple = cliente.uid(
            "FETCH", "11",
            "(UID BODY.PEEK[1.MIME] BODY.PEEK[1]<0.65536>)",
        )
        corpo_apple_bruto = repr(corpo_apple).encode()
        assert tipo == "OK"
        assert b"Content-Transfer-Encoding: 8bit" in corpo_apple_bruto
        assert b"Ol\\xc3\\xa1 pelo IMAP!" in corpo_apple_bruto

        # UID FETCH deve devolver UID implicitamente mesmo quando o cliente
        # pede apenas o corpo. O Apple Mail usa esse campo para associar o
        # literal recebido à mensagem local.
        tipo, corpo_com_uid_implícito = cliente.uid(
            "FETCH", "11", "(BODY.PEEK[] BODYSTRUCTURE)"
        )
        corpo_com_uid_bruto = repr(corpo_com_uid_implícito).encode()
        assert tipo == "OK"
        assert b"UID 11" in corpo_com_uid_bruto
        assert b"Ol\\xc3\\xa1 pelo IMAP!" in corpo_com_uid_bruto

        tipo, cabecalhos_excluidos = cliente.uid(
            "FETCH", "11",
            "(BODY.PEEK[HEADER.FIELDS.NOT (X-SEGREDO SUBJECT)])",
        )
        cabecalhos_brutos = repr(cabecalhos_excluidos).encode()
        assert tipo == "OK"
        assert b"Subject: Primeira carta" not in cabecalhos_brutos
        assert b"From: Ana" in cabecalhos_brutos

        tipo, _ = cliente.store("1", "+FLAGS", "(\\Seen)")
        assert tipo == "OK"
        tipo, não_lidas = cliente.search(None, "UNSEEN")
        assert tipo == "OK" and não_lidas == [b"2"]

        tipo, uids = cliente.uid("SEARCH", None, "ALL")
        assert tipo == "OK" and uids == [b"11 14"]

        # COPY conserva a origem e os sinalizadores, cria um novo UID no
        # destino e publica o mapeamento exigido por UIDPLUS.
        tipo, _ = cliente.uid("COPY", "11", "Arquivadas")
        nome_do_código, resposta_da_cópia = cliente.response("COPYUID")
        resposta_da_cópia_bruta = b" ".join(resposta_da_cópia or [])
        assert tipo == "OK"
        assert nome_do_código == "COPYUID"
        assert b"1788130000 11 1" in resposta_da_cópia_bruta
        tipo, quantidade = cliente.select("INBOX")
        assert tipo == "OK" and quantidade == [b"2"]
        tipo, quantidade = cliente.select("Arquivadas")
        assert tipo == "OK" and quantidade == [b"1"]
        tipo, dados_copiados = cliente.uid(
            "FETCH", "1", "(UID FLAGS BODY.PEEK[])"
        )
        dados_copiados_brutos = repr(dados_copiados).encode()
        assert tipo == "OK" and b"Primeira carta" in dados_copiados_brutos
        assert b"\\Seen" in dados_copiados_brutos
        tipo, quantidade = cliente.select("INBOX")
        assert tipo == "OK" and quantidade == [b"2"]

        tipo, _ = cliente.uid("MOVE", "14", "Arquivadas")
        assert tipo == "OK"

        tipo, quantidade = cliente.select("Arquivadas")
        assert tipo == "OK" and quantidade == [b"2"]
        tipo, _ = cliente.uid("MOVE", "2", "Lixeira")
        assert tipo == "OK"

        tipo, quantidade = cliente.select("Lixeira")
        assert tipo == "OK" and quantidade == [b"1"]

        # Um segundo cliente devolve a carta para INBOX enquanto o primeiro
        # está em IDLE. O primeiro precisa receber EXISTS sem fazer NOOP.
        tipo, quantidade = cliente.select("INBOX")
        assert tipo == "OK" and quantidade == [b"1"]
        cliente.sock.settimeout(4)
        cliente.send(b"ZZ01 IDLE\r\n")
        assert cliente.readline().startswith(b"+ ")

        outro = imaplib.IMAP4_SSL(
            "127.0.0.1", args.porta, ssl_context=contexto
        )
        tipo, _ = outro.login("teste@xn--santaf-gva.dev.br", "segredo")
        assert tipo == "OK"
        tipo, _ = outro.enable("UTF8=ACCEPT")
        assert tipo == "OK"
        tipo, _ = outro.select("Lixeira")
        assert tipo == "OK"
        tipo, _ = outro.uid("MOVE", "1", "INBOX")
        assert tipo == "OK"

        atualização = cliente.readline()
        assert atualização == b"* 2 EXISTS\r\n", atualização

        tipo, _ = outro.select("INBOX")
        assert tipo == "OK"
        tipo, _ = outro.uid("STORE", "15", "+FLAGS", "(\\Seen)")
        assert tipo == "OK"
        atualização = cliente.readline()
        assert b"FETCH (UID 15 FLAGS " in atualização, atualização
        assert b"\\Seen" in atualização, atualização

        tipo, _ = outro.uid("MOVE", "15", "Lixeira")
        assert tipo == "OK"
        atualização = cliente.readline()
        assert atualização == b"* 2 EXPUNGE\r\n", atualização
        outro.logout()

        cliente.send(b"DONE\r\n")
        assert cliente.readline().startswith(b"ZZ01 OK ")

        rascunho = (
            "Date: Mon, 31 Aug 2026 02:03:04 +0000\r\n"
            "From: teste@santafé.dev.br\r\n"
            "To: ana@example.net\r\n"
            "Subject: Rascunho pelo IMAP\r\n"
            "Message-ID: <rascunho-imap@santafé.dev.br>\r\n"
            "Content-Type: text/plain; charset=UTF-8\r\n\r\n"
            "Olá, este é um rascunho preservado."
        ).encode("utf-8")
        recusada_sem_marcador = anexe_literal(
            cliente, b"SFU0", "Rascunhos", rascunho,
            internacional=False,
            sinalizadores="(\\Seen \\Flagged \\Draft)",
            data_interna="31-Aug-2026 02:03:04 +0000",
        )
        assert b"SFU0 OK " in recusada_sem_marcador
        assert b"APPENDUID 1788130000 1" in recusada_sem_marcador

        quebrada = rascunho.replace(
            b"To: ana@example.net",
            "To: jos�@santafé.dev.br".encode("utf-8"),
        )
        resposta_quebrada = anexe_literal(
            cliente, b"SFU1", "Rascunhos", quebrada, internacional=True
        )
        assert b"SFU1 NO " in resposta_quebrada
        assert b"perdeu caracteres Unicode" in resposta_quebrada

        codificada = rascunho.replace(
            b"To: ana@example.net",
            b"To: =?utf-8?B?am9zw6k=?=@xn--santaf-gva.dev.br",
        )
        resposta_codificada = anexe_literal(
            cliente, b"SFU2", "Rascunhos", codificada, internacional=True
        )
        assert b"SFU2 NO " in resposta_codificada
        assert b"codificacao MIME dentro do endereco" in resposta_codificada

        identificação_codificada = rascunho.replace(
            b"Message-ID: <rascunho-imap@santaf\xc3\xa9.dev.br>",
            b"Message-ID: <=?utf-8?B?am9zw6k=?=@xn--santaf-gva.dev.br>",
        )
        resposta_identificação = anexe_literal(
            cliente, b"SFU3", "Rascunhos", identificação_codificada,
            internacional=True,
        )
        assert b"SFU3 NO " in resposta_identificação
        assert b"Message-ID nao aceita palavras MIME codificadas" in \
            resposta_identificação

        tipo, resposta = "OK", anexe_literal(
            cliente, b"SFU4", "Rascunhos", rascunho,
            internacional=True,
            sinalizadores="(\\Seen \\Flagged \\Draft)",
            data_interna="31-Aug-2026 02:03:04 +0000",
        )
        assert b"SFU4 OK " in resposta, resposta
        assert b"APPENDUID 1788130000 2" in resposta, resposta

        tipo, quantidade = cliente.select("Rascunhos")
        assert tipo == "OK" and quantidade == [b"2"]
        tipo, dados = cliente.fetch("1", "(FLAGS INTERNALDATE RFC822.SIZE)")
        assert tipo == "OK"
        bruto = repr(dados).encode()
        assert b"\\Seen" in bruto and b"\\Flagged" in bruto
        assert b"31-Aug-2026 02:03:04 +0000" in bruto
        tipo, dados = cliente.fetch("1", "(BODY.PEEK[])")
        assert tipo == "OK" and b"Rascunho pelo IMAP" in repr(dados).encode()
        tipo, _ = cliente.uid("STORE", "1:2", "+FLAGS", "(\\Deleted)")
        assert tipo == "OK"
        tipo, _ = cliente.uid("EXPUNGE", "1:2")
        assert tipo == "OK"
        tipo, quantidade = cliente.select("Rascunhos")
        assert tipo == "OK" and quantidade == [b"0"]

        enviada = (
            "Date: Mon, 31 Aug 2026 02:04:00 +0000\r\n"
            "From: teste@santafé.dev.br\r\n"
            "To: maria@example.org\r\n"
            "Subject: Cópia enviada\r\n"
            "Message-ID: <enviada-imap@santafé.dev.br>\r\n"
            "Content-Type: text/plain; charset=UTF-8\r\n\r\n"
            "A mesma cópia não pode ser duplicada."
        ).encode("utf-8")
        primeira = anexe_literal(
            cliente, b"SFU4", "Enviadas", enviada,
            internacional=True, sinalizadores="(\\Seen)"
        )
        assert b"SFU4 OK " in primeira and b"APPENDUID" in primeira
        segunda = anexe_literal(
            cliente, b"SFU5", "Enviadas", enviada,
            internacional=True, sinalizadores="(\\Seen)"
        )
        assert b"SFU5 OK " in segunda and b"APPENDUID" in segunda
        assert primeira.replace(b"SFU4", b"SFUX") == segunda.replace(
            b"SFU5", b"SFUX"
        )
        tipo, quantidade = cliente.select("Enviadas")
        assert tipo == "OK" and quantidade == [b"1"]

        # Na Lixeira, UID EXPUNGE remove definitivamente; CLOSE também
        # expurga em silêncio os itens marcados como \Deleted.
        tipo, quantidade = cliente.select("Lixeira")
        assert tipo == "OK" and quantidade == [b"3"]
        tipo, uids_na_lixeira = cliente.uid("SEARCH", None, "ALL")
        assert tipo == "OK"
        uids = uids_na_lixeira[0].split()
        assert len(uids) == 3
        primeiro_uid = uids[0].decode("ascii")
        tipo, _ = cliente.uid(
            "STORE", primeiro_uid, "+FLAGS", "(\\Deleted)"
        )
        assert tipo == "OK"

        # O Gmail móvel pode encerrar a conexão depois de STORE e abrir
        # outra somente para esvaziar a Lixeira. \Deleted precisa sobreviver.
        cliente.logout()
        cliente = imaplib.IMAP4_SSL(
            "127.0.0.1", args.porta, ssl_context=contexto
        )
        tipo, _ = cliente.login("teste@xn--santaf-gva.dev.br", "segredo")
        assert tipo == "OK"
        tipo, _ = cliente.enable("UTF8=ACCEPT")
        assert tipo == "OK"
        tipo, quantidade = cliente.select("Lixeira")
        assert tipo == "OK" and quantidade == [b"3"]
        tipo, marcas_persistidas = cliente.uid(
            "FETCH", primeiro_uid, "(FLAGS)"
        )
        assert tipo == "OK"
        assert b"\\Deleted" in repr(marcas_persistidas).encode()
        tipo, _ = cliente.uid("EXPUNGE", primeiro_uid)
        assert tipo == "OK"
        tipo, quantidade = cliente.select("Lixeira")
        assert tipo == "OK" and quantidade == [b"2"]
        tipo, _ = cliente.store("1:*", "+FLAGS", "(\\Deleted)")
        assert tipo == "OK"
        tipo, _ = cliente.close()
        assert tipo == "OK"
        tipo, quantidade = cliente.select("Lixeira")
        assert tipo == "OK" and quantidade == [b"0"]

        recusada = anexe_literal(
            cliente, b"SFU6", "INBOX", rascunho, internacional=True
        )
        assert b"SFU6 NO " in recusada
        assert b"somente Rascunhos ou Enviadas" in recusada
        cliente.logout()
        print(
            "Correio IMAP TLS, LOGIN, AUTH PLAIN, STATUS, LIST, FETCH parcial, "
            "STORE, SEARCH, COPY, MOVE, Arquivadas, IDLE ativo, UTF8=ACCEPT, "
            "APPEND UTF8, UIDPLUS e Lixeira: ok"
        )
    finally:
        if processo.poll() is None:
            processo.send_signal(signal.SIGTERM)
            try:
                processo.wait(timeout=2)
            except subprocess.TimeoutExpired:
                processo.kill()
                processo.wait(timeout=2)
        if processo.returncode not in (None, 0, -signal.SIGTERM):
            saida = processo.stdout.read().decode("utf-8", "replace")
            print(saida, file=sys.stderr)


if __name__ == "__main__":
    principal()
