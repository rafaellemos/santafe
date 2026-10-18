#!/usr/bin/env python3
"""Auditoria externa, somente de leitura, da identidade de um servidor postal.

Não envia cartas, não solicita credenciais e não altera DNS ou serviços.
Usa apenas a biblioteca-padrão do Python, `dig` e `openssl`.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import ipaddress
import json
import re
import shlex
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Iterable


class Analisador(argparse.ArgumentParser):
    def error(self, mensagem: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(2, f"ERRO: {mensagem}\n")


@dataclass
class Relatório:
    contagens: dict[str, int] = field(
        default_factory=lambda: {"OK": 0, "FALHA": 0, "AVISO": 0, "INFO": 0}
    )

    def registre(self, nível: str, título: str, detalhe: str = "") -> None:
        self.contagens[nível] += 1
        sufixo = f": {detalhe}" if detalhe else ""
        print(f"[{nível}] {título}{sufixo}")

    def ok(self, título: str, detalhe: str = "") -> None:
        self.registre("OK", título, detalhe)

    def falha(self, título: str, detalhe: str = "") -> None:
        self.registre("FALHA", título, detalhe)

    def aviso(self, título: str, detalhe: str = "") -> None:
        self.registre("AVISO", título, detalhe)

    def info(self, título: str, detalhe: str = "") -> None:
        self.registre("INFO", título, detalhe)


def domínio_ascii(domínio: str) -> str:
    limpo = domínio.strip().rstrip(".").lower()
    se_nulo = not limpo or any(not parte for parte in limpo.split("."))
    if se_nulo:
        raise ValueError("domínio vazio ou malformado")
    return limpo.encode("idna").decode("ascii")


def execute(comando: list[str], tempo: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        comando,
        check=False,
        capture_output=True,
        text=True,
        timeout=tempo,
    )


def dig(
    nome: str,
    tipo: str,
    resolvedor: str | None,
    tempo: int,
    curto: bool = True,
    dnssec: bool = False,
) -> str:
    comando = ["dig", f"+time={tempo}", "+tries=1"]
    if resolvedor:
        comando.append(f"@{resolvedor}")
    comando.extend([nome, tipo])
    if curto:
        comando.append("+short")
    else:
        comando.extend(["+noall", "+comments", "+answer"])
    if dnssec:
        comando.append("+dnssec")
    resultado = execute(comando, tempo + 2)
    if resultado.returncode != 0:
        erro = resultado.stderr.strip() or resultado.stdout.strip()
        raise RuntimeError(erro or f"dig terminou com código {resultado.returncode}")
    return resultado.stdout.strip()


def linhas(valor: str) -> list[str]:
    return [linha.strip() for linha in valor.splitlines() if linha.strip()]


def registros_txt(valor: str) -> list[str]:
    registros: list[str] = []
    for linha in linhas(valor):
        try:
            partes = shlex.split(linha)
        except ValueError:
            partes = re.findall(r'"((?:[^"\\]|\\.)*)"', linha)
        registros.append("".join(partes))
    return registros


def tem_marca_ad(resposta: str) -> bool:
    for linha in resposta.splitlines():
        if "flags:" in linha:
            campos = linha.split("flags:", 1)[1].split(";", 1)[0].split()
            return "ad" in campos
    return False


def seção(título: str) -> None:
    print(f"\n--- {título} ---")


def normalize_nome(nome: str) -> str:
    return nome.strip().rstrip(".").lower()


def confira_resolução(
    relatório: Relatório,
    domínio: str,
    nome_smtp: str,
    ip: ipaddress._BaseAddress,
    resolvedor: str,
    tempo: int,
) -> None:
    seção(f"DNS em {resolvedor}")
    tipo_endereço = "A" if ip.version == 4 else "AAAA"
    try:
        endereços_smtp = linhas(dig(nome_smtp, tipo_endereço, resolvedor, tempo))
        if str(ip) in endereços_smtp:
            relatório.ok("resolução direta do nome SMTP", f"{nome_smtp} → {ip}")
        else:
            relatório.falha(
                "resolução direta do nome SMTP",
                f"esperado {ip}; recebido {endereços_smtp or 'nada'}",
            )

        ptrs = linhas(dig(str(ip.reverse_pointer), "PTR", resolvedor, tempo))
        ptrs_normalizados = [normalize_nome(item) for item in ptrs]
        if normalize_nome(nome_smtp) in ptrs_normalizados:
            relatório.ok("resolução reversa", f"{ip} → {nome_smtp}")
        else:
            relatório.falha(
                "resolução reversa",
                f"esperado {nome_smtp}; recebido {ptrs or 'nada'}",
            )

        mx = linhas(dig(domínio, "MX", resolvedor, tempo))
        if not mx:
            relatório.falha("registro MX", "nenhum registro encontrado")
        else:
            relatório.ok("registro MX", "; ".join(mx))
            for registro in mx:
                partes = registro.split()
                alvo = normalize_nome(partes[-1]) if partes else ""
                if not alvo:
                    continue
                ipv4 = linhas(dig(alvo, "A", resolvedor, tempo))
                ipv6 = linhas(dig(alvo, "AAAA", resolvedor, tempo))
                if ipv4 or ipv6:
                    relatório.ok(
                        f"endereço do MX {alvo}", ", ".join(ipv4 + ipv6)
                    )
                else:
                    relatório.falha(f"endereço do MX {alvo}", "A/AAAA ausente")

        for nome, tipo, rótulo in (
            (nome_smtp, tipo_endereço, "DNSSEC direto"),
            (str(ip.reverse_pointer), "PTR", "DNSSEC reverso"),
        ):
            resposta = dig(nome, tipo, resolvedor, tempo, curto=False, dnssec=True)
            if tem_marca_ad(resposta):
                relatório.ok(rótulo, "cadeia validada pelo resolvedor (AD)")
            else:
                relatório.aviso(rótulo, "o resolvedor não devolveu a marca AD")
    except (RuntimeError, subprocess.TimeoutExpired) as erro:
        relatório.falha(f"consulta ao resolvedor {resolvedor}", str(erro))


def confira_spf(
    relatório: Relatório,
    domínio: str,
    ip: ipaddress._BaseAddress,
    resolvedor: str,
    tempo: int,
) -> None:
    try:
        valores = registros_txt(dig(domínio, "TXT", resolvedor, tempo))
    except (RuntimeError, subprocess.TimeoutExpired) as erro:
        relatório.falha("consulta SPF", str(erro))
        return
    registros = [valor for valor in valores if valor.lower().startswith("v=spf1")]
    if len(registros) != 1:
        relatório.falha(
            "SPF",
            "ausente" if not registros else f"{len(registros)} registros encontrados",
        )
        return
    registro = registros[0]
    relatório.ok("SPF único", registro)

    versão = "ip4" if ip.version == 4 else "ip6"
    autorizou = False
    for termo in registro.split()[1:]:
        mecanismo = termo.lstrip("+?~-")
        if not mecanismo.lower().startswith(f"{versão}:"):
            continue
        rede_texto = mecanismo.split(":", 1)[1]
        try:
            if ip in ipaddress.ip_network(rede_texto, strict=False):
                autorizou = not termo.startswith("-")
        except ValueError:
            relatório.falha("mecanismo SPF", f"endereço inválido: {termo}")
    if autorizou:
        relatório.ok("SPF autoriza o IP de saída", str(ip))
    elif any(t.lstrip("+?~-").startswith(("include:", "redirect=")) for t in registro.split()):
        relatório.aviso(
            "autorização SPF indireta",
            "o auditor não executa recursivamente include/redirect",
        )
    else:
        relatório.falha("SPF não autoriza diretamente o IP", str(ip))

    finalizadores = [t for t in registro.split() if t.endswith("all")]
    if finalizadores and finalizadores[-1] == "-all":
        relatório.ok("política final SPF", "-all")
    elif finalizadores:
        relatório.aviso("política final SPF", finalizadores[-1])
    else:
        relatório.aviso("política final SPF", "mecanismo all ausente")


def campos_separados(registro: str) -> dict[str, str]:
    campos: dict[str, str] = {}
    for parte in registro.split(";"):
        if "=" not in parte:
            continue
        chave, valor = parte.split("=", 1)
        campos[chave.strip().lower()] = valor.strip()
    return campos


def confira_dmarc(
    relatório: Relatório,
    domínio: str,
    resolvedor: str,
    tempo: int,
) -> None:
    nome = f"_dmarc.{domínio}"
    try:
        valores = registros_txt(dig(nome, "TXT", resolvedor, tempo))
    except (RuntimeError, subprocess.TimeoutExpired) as erro:
        relatório.falha("consulta DMARC", str(erro))
        return
    registros = [valor for valor in valores if valor.upper().startswith("V=DMARC1")]
    if len(registros) != 1:
        relatório.falha(
            "DMARC",
            "ausente" if not registros else f"{len(registros)} registros encontrados",
        )
        return
    registro = registros[0]
    campos = campos_separados(registro)
    política = campos.get("p", "")
    if política not in {"none", "quarantine", "reject"}:
        relatório.falha("política DMARC", política or "campo p ausente")
    elif política == "none":
        relatório.aviso("DMARC em observação", registro)
    else:
        relatório.ok("DMARC com imposição", registro)
    relatório.info(
        "alinhamento DMARC",
        f"DKIM={campos.get('adkim', 'r')}; SPF={campos.get('aspf', 'r')}",
    )
    if "rua" not in campos:
        relatório.aviso("relatórios agregados DMARC", "campo rua ausente")


def tamanho_chave_dkim(chave: str, tempo: int) -> int | None:
    try:
        binário = base64.b64decode(chave, validate=True)
    except (binascii.Error, ValueError):
        return None
    with tempfile.NamedTemporaryFile() as arquivo:
        arquivo.write(binário)
        arquivo.flush()
        resultado = execute(
            [
                "openssl",
                "pkey",
                "-pubin",
                "-inform",
                "DER",
                "-in",
                arquivo.name,
                "-text",
                "-noout",
            ],
            tempo,
        )
    if resultado.returncode != 0:
        return None
    encontrado = re.search(r"Public-Key:\s*\((\d+) bit\)", resultado.stdout)
    return int(encontrado.group(1)) if encontrado else None


def confira_dkim(
    relatório: Relatório,
    domínio: str,
    seletor: str,
    resolvedor: str,
    tempo: int,
) -> None:
    nome = f"{seletor}._domainkey.{domínio}"
    try:
        valores = registros_txt(dig(nome, "TXT", resolvedor, tempo))
    except (RuntimeError, subprocess.TimeoutExpired) as erro:
        relatório.falha("consulta DKIM", str(erro))
        return
    registros = [
        valor
        for valor in valores
        if valor.upper().startswith("V=DKIM1") or "p=" in valor
    ]
    if len(registros) != 1:
        relatório.falha(
            "DKIM",
            "ausente" if not registros else f"{len(registros)} registros encontrados",
        )
        return
    campos = campos_separados(registros[0])
    chave = "".join(campos.get("p", "").split())
    if not chave:
        relatório.falha("chave DKIM", "campo p ausente ou revogado")
        return
    tamanho = tamanho_chave_dkim(chave, tempo)
    if tamanho is None:
        relatório.falha("chave DKIM", "Base64 ou chave pública inválida")
    elif tamanho < 1024:
        relatório.falha("tamanho da chave DKIM", f"{tamanho} ticos")
    elif tamanho < 2048:
        relatório.aviso("tamanho da chave DKIM", f"{tamanho} ticos; prefira 2048")
    else:
        relatório.ok("chave DKIM", f"{tamanho} ticos; seletor {seletor}")


def leia_resposta_smtp(fluxo) -> tuple[int, list[str]]:
    respostas: list[str] = []
    código = 0
    while True:
        linha = fluxo.readline(65537)
        if not linha:
            raise RuntimeError("servidor SMTP encerrou a conexão")
        texto = linha.decode("utf-8", "replace").rstrip("\r\n")
        respostas.append(texto)
        if len(texto) >= 3 and texto[:3].isdigit():
            código = int(texto[:3])
            if len(texto) == 3 or texto[3:4] == " ":
                return código, respostas


def envie_smtp(conexão: socket.socket, comando: str) -> None:
    conexão.sendall(comando.encode("ascii") + b"\r\n")


def capacidades_smtp(respostas: Iterable[str]) -> set[str]:
    capacidades: set[str] = set()
    for resposta in respostas:
        conteúdo = resposta[4:].strip() if len(resposta) > 4 else ""
        if conteúdo:
            capacidades.add(conteúdo.split()[0].upper())
    return capacidades


def confira_smtp(
    relatório: Relatório,
    endereço: str,
    porta: int,
    nome_smtp: str,
    tempo: int,
) -> None:
    seção(f"SMTP {endereço}:{porta}")
    conexão: socket.socket | None = None
    try:
        conexão = socket.create_connection((endereço, porta), timeout=tempo)
        conexão.settimeout(tempo)
        fluxo = conexão.makefile("rb")
        código, saudação = leia_resposta_smtp(fluxo)
        if código != 220:
            raise RuntimeError("saudação SMTP: " + " | ".join(saudação))
        relatório.ok("porta SMTP acessível", saudação[-1])

        envie_smtp(conexão, "EHLO auditoria.invalid")
        código, respostas = leia_resposta_smtp(fluxo)
        if código != 250:
            raise RuntimeError("EHLO recusado: " + " | ".join(respostas))
        capacidades = capacidades_smtp(respostas)
        for capacidade in ("STARTTLS", "SMTPUTF8", "8BITMIME"):
            if capacidade in capacidades:
                relatório.ok(f"capacidade {capacidade}")
            else:
                relatório.falha(f"capacidade {capacidade}", "não anunciada")

        if "STARTTLS" not in capacidades:
            return
        envie_smtp(conexão, "STARTTLS")
        código, respostas = leia_resposta_smtp(fluxo)
        if código != 220:
            raise RuntimeError("STARTTLS recusado: " + " | ".join(respostas))
        fluxo.close()

        contexto = ssl.create_default_context()
        tls = contexto.wrap_socket(conexão, server_hostname=nome_smtp)
        conexão = tls
        fluxo = tls.makefile("rb")
        certificado = tls.getpeercert()
        relatório.ok(
            "certificado TLS",
            f"nome {nome_smtp}; protocolo {tls.version()}; expira {certificado.get('notAfter', '?')}",
        )
        envie_smtp(tls, "EHLO auditoria.invalid")
        código, respostas = leia_resposta_smtp(fluxo)
        if código != 250:
            raise RuntimeError("EHLO sob TLS recusado: " + " | ".join(respostas))
        capacidades_tls = capacidades_smtp(respostas)
        for capacidade in ("SMTPUTF8", "8BITMIME"):
            if capacidade in capacidades_tls:
                relatório.ok(f"{capacidade} sob TLS")
            else:
                relatório.falha(f"{capacidade} sob TLS", "não anunciada")
        envie_smtp(tls, "QUIT")
        leia_resposta_smtp(fluxo)
    except (OSError, RuntimeError, ssl.SSLError, socket.timeout) as erro:
        relatório.falha("ensaio SMTP/TLS", str(erro))
    finally:
        if conexão:
            try:
                conexão.close()
            except OSError:
                pass


def confira_rpki(
    relatório: Relatório,
    prefixo: str | None,
    asn: str | None,
    tempo: int,
) -> None:
    seção("Roteamento")
    if not prefixo or not asn:
        relatório.info(
            "RPKI não consultado", "forneça --prefixo-rpki e --asn"
        )
        return
    try:
        rede = ipaddress.ip_network(prefixo, strict=True)
    except ValueError as erro:
        relatório.falha("prefixo RPKI", str(erro))
        return
    asn_limpo = asn.upper().removeprefix("AS")
    if not asn_limpo.isdigit():
        relatório.falha("ASN", f"valor inválido: {asn}")
        return
    consulta = urllib.parse.urlencode(
        {"resource": f"AS{asn_limpo}", "prefix": str(rede)}
    )
    url = f"https://stat.ripe.net/data/rpki-validation/data.json?{consulta}"
    try:
        with urllib.request.urlopen(url, timeout=tempo) as resposta:
            dados = json.load(resposta)["data"]
    except (OSError, KeyError, ValueError, urllib.error.URLError) as erro:
        relatório.aviso("consulta RPKI indisponível", str(erro))
        return
    estado = dados.get("status", "desconhecido")
    detalhe = f"{rede} → AS{asn_limpo}"
    if estado == "valid":
        relatório.ok("origem BGP autorizada por RPKI", detalhe)
    elif estado == "unknown":
        relatório.aviso("RPKI sem ROA", detalhe)
    else:
        relatório.falha("RPKI inválido", f"{detalhe}; estado {estado}")


def confira_lista_spamhaus(
    relatório: Relatório, ip: ipaddress._BaseAddress, tempo: int
) -> None:
    if ip.version != 4:
        relatório.info("Spamhaus ZEN", "consulta automática limitada a IPv4")
        return
    nome = ".".join(reversed(str(ip).split("."))) + ".zen.spamhaus.org"
    try:
        respostas = linhas(dig(nome, "A", None, tempo))
    except (RuntimeError, subprocess.TimeoutExpired) as erro:
        relatório.aviso("Spamhaus ZEN", f"consulta indisponível: {erro}")
        return
    if not respostas:
        relatório.ok("Spamhaus ZEN", "nenhuma inclusão devolvida")
        return
    especiais = {"127.255.255.252", "127.255.255.254", "127.255.255.255"}
    if set(respostas) & especiais:
        relatório.info(
            "Spamhaus ZEN inconclusivo",
            "a consulta passou por resolvedor público ou atingiu limite",
        )
    else:
        relatório.falha("Spamhaus ZEN", ", ".join(respostas))


def argumentos() -> argparse.Namespace:
    analisador = Analisador(
        add_help=False,
        description="Audita DNS, SMTP/TLS, DNSSEC, RPKI e reputação básica.",
    )
    analisador._positionals.title = "argumentos"
    analisador._optionals.title = "opções"
    analisador.add_argument("-h", "--ajuda", action="help", help="mostra esta ajuda")
    analisador.add_argument("domínio", help="domínio do remetente")
    analisador.add_argument("--ip", required=True, help="IP público de saída")
    analisador.add_argument("--seletor", required=True, help="seletor DKIM")
    analisador.add_argument(
        "--nome-smtp",
        help="nome usado no EHLO e no certificado; por padrão, o domínio",
    )
    analisador.add_argument(
        "--endereço-smtp",
        help="endereço usado no ensaio SMTP; por padrão, o nome SMTP",
    )
    analisador.add_argument("--porta-smtp", type=int, default=25)
    analisador.add_argument(
        "--resolvedores", default="1.1.1.1,8.8.8.8", help="lista separada por vírgula"
    )
    analisador.add_argument("--prefixo-rpki", help="exemplo: 143.208.252.0/22")
    analisador.add_argument("--asn", help="exemplo: AS265132")
    analisador.add_argument("--tempo", type=int, default=8, help="limite por operação")
    return analisador.parse_args()


def principal() -> int:
    args = argumentos()
    for programa in ("dig", "openssl"):
        if not shutil.which(programa):
            print(f"ERRO: programa obrigatório não encontrado: {programa}", file=sys.stderr)
            return 2
    try:
        domínio = domínio_ascii(args.domínio)
        nome_smtp = domínio_ascii(args.nome_smtp or domínio)
        ip = ipaddress.ip_address(args.ip)
    except ValueError as erro:
        print(f"ERRO: {erro}", file=sys.stderr)
        return 2
    if not 1 <= args.porta_smtp <= 65535 or args.tempo < 1:
        print("ERRO: porta ou tempo inválido", file=sys.stderr)
        return 2
    resolvedores = [item.strip() for item in args.resolvedores.split(",") if item.strip()]
    if not resolvedores:
        print("ERRO: informe ao menos um resolvedor", file=sys.stderr)
        return 2

    relatório = Relatório()
    print("Auditoria da identidade postal")
    print(f"Domínio informado: {args.domínio}")
    print(f"Domínio DNS: {domínio}")
    print(f"Nome SMTP: {nome_smtp}")
    print(f"IP de saída: {ip}")

    for resolvedor in resolvedores:
        confira_resolução(
            relatório, domínio, nome_smtp, ip, resolvedor, args.tempo
        )

    seção("Autenticação postal")
    resolvedor_principal = resolvedores[0]
    confira_spf(relatório, domínio, ip, resolvedor_principal, args.tempo)
    confira_dkim(
        relatório, domínio, args.seletor, resolvedor_principal, args.tempo
    )
    confira_dmarc(relatório, domínio, resolvedor_principal, args.tempo)

    confira_smtp(
        relatório,
        args.endereço_smtp or nome_smtp,
        args.porta_smtp,
        nome_smtp,
        args.tempo,
    )
    confira_rpki(relatório, args.prefixo_rpki, args.asn, args.tempo)

    seção("Reputação básica")
    confira_lista_spamhaus(relatório, ip, args.tempo)
    relatório.info(
        "limite da auditoria",
        "classificações internas de destinatários, como o Gmail, não são públicas",
    )

    seção("Resumo")
    print(
        " ".join(
            f"{nome}={relatório.contagens[nome]}"
            for nome in ("OK", "FALHA", "AVISO", "INFO")
        )
    )
    if relatório.contagens["FALHA"]:
        print("Resultado: existem falhas técnicas a corrigir.")
        return 1
    if relatório.contagens["AVISO"]:
        print("Resultado: identidade funcional, com avisos a examinar.")
        return 0
    print("Resultado: identidade técnica validada sem ressalvas detectáveis.")
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
