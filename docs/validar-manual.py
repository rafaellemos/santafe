#!/usr/bin/env python3
"""Valida a estrutura e os exemplos executáveis do manual Santafé."""

from __future__ import annotations

import argparse
import html
from html.parser import HTMLParser
from pathlib import Path
import re
import subprocess
import tempfile


CONTRATOS_C = (
    ("src/lbaselib.c", "base_funcs", "", set()),
    ("src/lstrlib.c", "strlib", "colar.", set()),
    ("src/ltablib.c", "tab_funcs", "tabela.", set()),
    ("src/lmathlib.c", "mathlib", "mat.", set()),
    ("src/loslib.c", "syslib", "so.", set()),
    ("src/liolib.c", "iolib", "es.", set()),
    ("src/liolib.c", "flib", "arquivo:", set()),
    ("src/lcorolib.c", "co_funcs", "corrotina.", set()),
    ("src/lutf8lib.c", "funcs", "utf8.", set()),
    ("src/ldblib.c", "dblib", "depure.", set()),
    ("src/loadlib.c", "pk_funcs", "módulo.", set()),
    ("bibs/bibc/segredo/segredo.c", "segredo_funções", "segredo.", set()),
    ("bibs/bibc/rede/rede.c", "pclient_methods", "cliente:", set()),
    ("bibs/bibc/rede/rede.c", "pserver_methods", "servidor:", set()),
    ("bibs/bibc/rede/rede.c", "pconn_methods", "conexão:", set()),
    ("bibs/bibc/rede/rede.c", "pudp_methods", "udp:", set()),
    ("bibs/bibc/rede/rede.c", "ptimer_methods", "agendamento:", set()),
    ("bibs/bibc/rede/rede.c", "rede_funcs", "rede.", set()),
    ("bibs/bibc/mariadb/mariadb.c", "pool_methods", "piscina:", set()),
    ("bibs/bibc/mariadb/mariadb.c", "session_methods", "sessão:", set()),
    ("bibs/bibc/mariadb/mariadb.c", "transaction_methods", "transação:", set()),
    ("bibs/bibc/mariadb/mariadb.c", "con_methods", "conexão:", set()),
    ("bibs/bibc/mariadb/mariadb.c", "stmt_methods", "consulta:", set()),
    ("bibs/bibc/mariadb/mariadb.c", "res_methods", "resultado:", set()),
    ("bibs/bibc/mariadb/mariadb.c", "mysql_funcs", "mariadb.", set()),
    ("bibs/bibc/arquivo/arquivo.c", "arquivo_funções", "arquivo.", set()),
)


class Coletor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []
        self.links_internos: list[str] = []
        self.alvos_execucao: list[str] = []
        self.alvos_copia: list[str] = []
        self.linhas_funcoes = 0
        self.detalhes_funcoes = 0
        self._codigo_id: str | None = None
        self._codigo_partes: list[str] = []
        self.codigos: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs_lista: list[tuple[str, str | None]]) -> None:
        attrs = dict(attrs_lista)
        identificador = attrs.get("id")
        if identificador:
            self.ids.append(identificador)

        classes = set((attrs.get("class") or "").split())
        if "sf-fn-row" in classes:
            self.linhas_funcoes += 1
        if "sf-fn-detail-row" in classes:
            self.detalhes_funcoes += 1

        href = attrs.get("href")
        if href and href.startswith("#") and len(href) > 1:
            self.links_internos.append(href[1:])

        alvo_execucao = attrs.get("data-run-target")
        if alvo_execucao:
            self.alvos_execucao.append(alvo_execucao.removeprefix("#"))

        alvo_copia = attrs.get("data-copy-target")
        if alvo_copia:
            self.alvos_copia.append(alvo_copia.removeprefix("#"))

        if tag == "code" and identificador:
            self._codigo_id = identificador
            self._codigo_partes = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "code" and self._codigo_id is not None:
            self.codigos[self._codigo_id] = "".join(self._codigo_partes)
            self._codigo_id = None
            self._codigo_partes = []

    def handle_data(self, data: str) -> None:
        if self._codigo_id is not None:
            self._codigo_partes.append(data)


def duplicados(itens: list[str]) -> list[str]:
    vistos: set[str] = set()
    repetidos: set[str] = set()
    for item in itens:
        if item in vistos:
            repetidos.add(item)
        vistos.add(item)
    return sorted(repetidos)


def validar_exemplos(coletor: Coletor, compilador: Path) -> list[str]:
    falhas: list[str] = []
    if not compilador.is_file():
        return [f"compilador não encontrado: {compilador}"]

    with tempfile.TemporaryDirectory(prefix="santafe-manual-") as pasta:
        pasta_temp = Path(pasta)
        for numero, alvo in enumerate(dict.fromkeys(coletor.alvos_execucao), 1):
            codigo = coletor.codigos.get(alvo)
            if codigo is None:
                continue
            arquivo = pasta_temp / f"exemplo-{numero}.fé"
            arquivo.write_text(html.unescape(codigo), encoding="utf-8")
            resultado = subprocess.run(
                [str(compilador), "-p", str(arquivo)],
                text=True,
                capture_output=True,
            )
            if resultado.returncode != 0:
                mensagem = (resultado.stderr or resultado.stdout).strip().replace("\n", " | ")
                falhas.append(f"{alvo}: {mensagem}")
    return falhas


def decodificar_literal_c(partes: list[str]) -> str:
    """Decodifica a forma usada pelos registros luaL_Reg do projeto."""
    dados = bytearray()
    escapes = {"n": 10, "r": 13, "t": 9, "\\": 92, '"': 34}
    for parte in partes:
        posição = 0
        while posição < len(parte):
            if parte[posição : posição + 2] == "\\x":
                fim = posição + 2
                while fim < min(posição + 4, len(parte)) and parte[fim] in "0123456789abcdefABCDEF":
                    fim += 1
                dados.append(int(parte[posição + 2 : fim], 16))
                posição = fim
            elif parte[posição] == "\\" and posição + 1 < len(parte):
                caractere = parte[posição + 1]
                dados.append(escapes.get(caractere, ord(caractere)))
                posição += 2
            else:
                dados.extend(parte[posição].encode("utf-8"))
                posição += 1
    return dados.decode("utf-8")


def funções_do_registro_c(arquivo: Path, nome: str) -> list[str]:
    texto = arquivo.read_text(encoding="utf-8")
    matriz = re.search(
        rf"(?:static\s+)?(?:const\s+)?luaL_Reg\s+{re.escape(nome)}\[\]\s*=\s*\{{(.*?)\n\}};",
        texto,
        re.S,
    )
    if matriz is None:
        raise ValueError(f"registro luaL_Reg ausente: {arquivo}:{nome}")

    funções: list[str] = []
    for campo in re.findall(r'\{\s*((?:"(?:\\.|[^"\\])*"\s*)+)\s*,', matriz.group(1)):
        partes = re.findall(r'"((?:\\.|[^"\\])*)"', campo)
        funções.append(decodificar_literal_c(partes))
    return funções


def nomes_documentados(texto: str) -> set[str]:
    nomes: set[str] = set()
    células = re.findall(r"<tr(?:\s[^>]*)?>\s*<td(?:\s[^>]*)?>(.*?)</td>", texto, re.S)
    for célula in células:
        for valor in re.findall(r"<code(?:\s[^>]*)?>(.*?)</code>", célula, re.S):
            nome = html.unescape(re.sub(r"<[^>]+>", "", valor)).strip()
            nome = re.sub(r"\s*\(.*$", "", nome)
            if nome:
                nomes.add(nome)
    return nomes


def localizar_fonte(pasta_do_validador: Path, fonte_informado: Path | None) -> Path | None:
    candidatos = [fonte_informado] if fonte_informado else [
        pasta_do_validador.parent,
        pasta_do_validador.parent / "fonte",
    ]
    for candidato in candidatos:
        if candidato is not None and (candidato / "src/lbaselib.c").is_file():
            return candidato.resolve()
    return None


def validar_api_c(texto: str, fonte: Path) -> tuple[list[str], int]:
    documentados = nomes_documentados(texto)
    problemas: list[str] = []
    conferidas = 0
    for caminho, matriz, prefixo, exceções in CONTRATOS_C:
        arquivo = fonte / caminho
        if not arquivo.is_file():
            problemas.append(f"fonte da API ausente: {arquivo}")
            continue
        try:
            nomes = funções_do_registro_c(arquivo, matriz)
        except ValueError as falha:
            problemas.append(str(falha))
            continue
        for nome in nomes:
            if nome.startswith("__") or nome in exceções:
                continue
            conferidas += 1
            contrato = prefixo + nome
            if contrato not in documentados:
                problemas.append(f"API pública sem entrada no manual: {contrato}")
    return problemas, conferidas


def leia_manifesto_fe(caminho: Path) -> tuple[list[tuple[str, str]], list[str]]:
    contratos: list[tuple[str, str]] = []
    problemas: list[str] = []
    vistos: set[tuple[str, str]] = set()
    for número, linha in enumerate(caminho.read_text(encoding="utf-8").splitlines(), 1):
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue
        partes = [parte.strip() for parte in linha.split("|")]
        if len(partes) != 2 or not all(partes):
            problemas.append(f"manifesto Fé inválido na linha {número}: esperado contrato|fonte")
            continue
        entrada = (partes[0], partes[1])
        if entrada in vistos:
            problemas.append(f"contrato Fé repetido no manifesto: {partes[0]} ({partes[1]})")
            continue
        vistos.add(entrada)
        contratos.append(entrada)
    return contratos, problemas


def nome_final_do_contrato(contrato: str) -> str:
    nome = re.split(r"[.:]", contrato)[-1]
    return nome.strip()


def fonte_declara_nome(texto: str, nome: str) -> bool:
    escapado = re.escape(nome)
    texto_decodificado = re.sub(
        r"(?:\\x[0-9A-Fa-f]{2})+",
        lambda ocorrência: bytes(
            int(valor, 16) for valor in re.findall(r"\\x([0-9A-Fa-f]{2})", ocorrência.group(0))
        ).decode("utf-8", errors="replace"),
        texto,
    )
    texto_decodificado = re.sub(r'"\s*"', "", texto_decodificado)
    padrões = (
        rf"\bfunção\s+{escapado}\s*\(",
        rf"\bfunção\s+[\wÀ-ÿ.:]+{escapado}\s*\(",
        rf"\b{escapado}\s*=\s*função\s*\(",
        rf"\b[\wÀ-ÿ]+\.{escapado}\s*=",
        rf"\b{escapado}\s*=",
        rf'"{escapado}"',
    )
    return any(re.search(padrão, texto_decodificado) for padrão in padrões)


def validar_api_fe(texto: str, fonte: Path, manifesto: Path) -> tuple[list[str], int]:
    problemas: list[str] = []
    if not manifesto.is_file():
        return [f"manifesto da API Fé ausente: {manifesto}"], 0

    contratos, falhas = leia_manifesto_fe(manifesto)
    problemas.extend(falhas)
    documentados = nomes_documentados(texto)
    arquivos: dict[Path, str] = {}
    conferidas = 0
    for contrato, caminho in contratos:
        arquivo = fonte / caminho
        if not arquivo.is_file():
            problemas.append(f"fonte do contrato Fé ausente: {arquivo}")
            continue
        if contrato not in documentados:
            problemas.append(f"API pública Fé sem entrada no manual: {contrato}")
        conteúdo = arquivos.setdefault(arquivo, arquivo.read_text(encoding="utf-8"))
        nome = nome_final_do_contrato(contrato)
        if not fonte_declara_nome(conteúdo, nome):
            problemas.append(
                f"contrato Fé não localizado no fonte: {contrato} ({caminho})"
            )
        conferidas += 1
    return problemas, conferidas


def main() -> int:
    pasta = Path(__file__).resolve().parent
    analisador = argparse.ArgumentParser()
    analisador.add_argument("manual", nargs="?", type=Path, default=pasta / "manual.html")
    analisador.add_argument(
        "--compilador",
        type=Path,
    )
    analisador.add_argument(
        "--fonte",
        type=Path,
        help="raiz do fonte usada para conferir as APIs públicas C e Fé",
    )
    analisador.add_argument(
        "--api-fe",
        type=Path,
        help="manifesto explícito da API pública das bibliotecas Fé",
    )
    args = analisador.parse_args()
    fonte = localizar_fonte(pasta, args.fonte)
    if args.compilador is None:
        if fonte is None:
            analisador.error("informe --fonte ou --compilador; núcleo não localizado")
        args.compilador = fonte / "src/santafec"

    texto = args.manual.read_text(encoding="utf-8")
    coletor = Coletor()
    coletor.feed(texto)

    problemas: list[str] = []
    ids = set(coletor.ids)

    for identificador in duplicados(coletor.ids):
        problemas.append(f"identificador repetido: #{identificador}")
    for ancora in sorted(set(coletor.links_internos) - ids):
        problemas.append(f"âncora interna sem destino: #{ancora}")
    for alvo in sorted(set(coletor.alvos_execucao + coletor.alvos_copia) - set(coletor.codigos)):
        problemas.append(f"botão aponta para código inexistente: #{alvo}")
    if coletor.linhas_funcoes != coletor.detalhes_funcoes:
        problemas.append(
            "quantidade desigual de linhas e detalhes de funções: "
            f"{coletor.linhas_funcoes} != {coletor.detalhes_funcoes}"
        )

    grupos = re.findall(r'<tr class="sf-fn-row"[^>]*>\s*<td>(.*?)</td>', texto, re.S)
    agrupados = [grupo for grupo in grupos if len(re.findall(r"<code(?:\s[^>]*)?>", grupo)) > 1]
    if agrupados:
        problemas.append(f"{len(agrupados)} linha(s) ainda agrupam mais de uma função")

    linhas_brutas = re.findall(r'<tr class="sf-fn-row".*?</tr>', texto, re.S)
    for numero, linha in enumerate(linhas_brutas, 1):
        if linha.count("<td>") != 2 or linha.count("</td>") != 2:
            problemas.append(f"linha de função {numero} não possui exatamente duas células")
        if linha.count("sf-fn-chevron") != 1:
            problemas.append(f"linha de função {numero} não possui exatamente uma seta")
    if re.search(r'id="[^"]*<', texto):
        problemas.append("marca HTML encontrada dentro de um identificador")

    problemas.extend(f"exemplo não compila: {falha}" for falha in validar_exemplos(coletor, args.compilador))

    fonte = localizar_fonte(pasta, args.fonte)
    api_conferidas = 0
    api_fe_conferidas = 0
    if fonte is None:
        problemas.append("raiz do fonte não localizada para conferir as APIs públicas")
    else:
        falhas_api, api_conferidas = validar_api_c(texto, fonte)
        problemas.extend(falhas_api)
        manifesto_fe = args.api_fe or fonte / "docs/API-PUBLICA-FE.tsv"
        falhas_fe, api_fe_conferidas = validar_api_fe(texto, fonte, manifesto_fe)
        problemas.extend(falhas_fe)

    print(f"IDs: {len(coletor.ids)}")
    print(f"Funções colapsáveis: {coletor.linhas_funcoes}")
    print(f"Exemplos executáveis: {len(set(coletor.alvos_execucao))}")
    print(f"Contratos C conferidos: {api_conferidas}")
    print(f"Contratos Fé conferidos: {api_fe_conferidas}")
    if problemas:
        print("\nProblemas:")
        for problema in problemas:
            print(f"- {problema}")
        return 1

    print("Manual validado sem problemas estruturais ou sintáticos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
