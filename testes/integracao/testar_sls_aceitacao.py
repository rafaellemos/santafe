#!/usr/bin/env python3
"""Executa a bateria SLS atual ou o contrato-alvo 1.0, sem instalar nada.

Saídas: 0 = critérios executados aprovados; 1 = falha; 2 = capacidade pendente.
Automação verde não libera 1.0 enquanto houver gates de homologação externa.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time

from sls.casos import CASOS
from sls.cliente import Cliente, Pendente


RAIZ = Path(__file__).resolve().parents[2]
GATES_EXTERNOS = {
    "vscode-real": "Diagnóstico, conclusões, navegação, rename e reinício no VS Code, sem provedor local mascarando o SLS.",
    "sublime-real": "Mesmos recursos no Sublime/LSP, inclusive edição Unicode e restart.",
    "instalacao-limpa": "macOS e Linux: prefixos de usuário/com espaços, atualização, remoção, sem sudo; Windows precisa de matriz explícita de suporte.",
    "distribuicao": "Fonte, binário instalado e serverInfo coincidem; hashes, licenças, manual, downloads e pacotes dos editores conferidos.",
    "carga-e-isolamento": "Projeto grande, latência p95, memória, cancelamento durante análise, raízes múltiplas, symlinks e limites de indexação.",
    "revisao-semantica": "Revisão do analisador: recuperação após erros, múltiplos diagnósticos, tabelas/metatabelas dinâmicas, imports cíclicos e exports ambíguos.",
}


def estado(perfil, resultados, parcial=False):
    totais = {chave: sum(item["estado"] == chave for item in resultados)
              for chave in ("OK", "FALHA", "PENDENTE")}
    if totais["FALHA"]:
        codigo = 1
    elif totais["PENDENTE"]:
        codigo = 2
    else:
        codigo = 0
    return {"totais": totais, "codigo_saida": codigo,
            "perfil_atual_aprovado": perfil == "atual" and codigo == 0 and not parcial,
            "automacao_alvo_aprovada": perfil == "1.0" and codigo == 0 and not parcial,
            # Uma execução local nunca substitui os gates de instalação/editores/distribuição.
            "liberavel_como_1_0": False}


def procedencia(comando):
    def git(*argumentos):
        retorno = subprocess.run(["git", *argumentos], cwd=str(RAIZ), capture_output=True, timeout=10)
        return retorno.stdout.decode("utf-8", errors="replace").strip() if retorno.returncode == 0 else None
    fonte = RAIZ / "ferramentas/sls/sls.fé"
    pasta = RAIZ / "testes/integracao"
    arquivos = [pasta / "testar_sls_aceitacao.py", pasta / "testar_sls_infraestrutura.py",
                pasta / "testar_sls_incremental.py", pasta / "testar_analise_c.py",
                *sorted((pasta / "sls").glob("*.py")), pasta / "sls/analise_c.c"]
    return {"instante_utc": datetime.now(timezone.utc).isoformat(), "plataforma": platform.platform(),
            "python": platform.python_version(), "comando": comando, "git_commit": git("rev-parse", "HEAD"),
            "git_modificado": bool(git("status", "--porcelain")),
            "fonte_repositorio_sha256": hashlib.sha256(fonte.read_bytes()).hexdigest(),
            "bateria_sha256": {str(arquivo.relative_to(RAIZ)): hashlib.sha256(arquivo.read_bytes()).hexdigest()
                               for arquivo in arquivos},
            "nota_hash": "Hash do fonte local; --comando pode apontar para outra instalação. Veja serverInfo de cada ensaio."}


def principal(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--perfil", choices=("atual", "1.0"), default="atual")
    parser.add_argument("--listar", action="store_true", help="lista critérios sem executar o SLS")
    parser.add_argument("--caso", action="append", help="executa somente IDs selecionados (não homologa o perfil completo)")
    parser.add_argument("--comando", nargs="+", help="iniciador instalado, sem shell; padrão: núcleo e SLS do repositório")
    parser.add_argument("--prazo", type=float, default=5, help="prazo por resposta em segundos; padrão 5")
    parser.add_argument("--relatorio", type=Path, help="salva relatório JSON, inclusive em caso de falha")
    args = parser.parse_args(argv)
    if not 0.1 <= args.prazo <= 30:
        parser.error("--prazo precisa estar entre 0.1 e 30 segundos")
    casos = [item for item in CASOS if args.perfil == "1.0" or item["perfil"] == "atual"]
    if args.caso:
        desconhecidos = set(args.caso) - {item["id"] for item in casos}
        if desconhecidos:
            parser.error("IDs fora deste perfil: " + ", ".join(sorted(desconhecidos)))
        casos = [item for item in casos if item["id"] in args.caso]
    if args.listar:
        for item in casos:
            print(f"{item['id']} | {item['grupo']} | {item['perfil']}")
        print(f"Critérios executáveis: {len(casos)}")
        return 0
    comando = args.comando or [os.environ.get("SANTAFE_TEST_BIN", str(RAIZ / "src/santafé")),
                              str(RAIZ / "ferramentas/sls/sls.fé")]
    resultados = []
    origem = procedencia(comando)
    print(f"Bateria SLS — perfil {args.perfil}; {len(casos)} critérios; sem instalação/publicação")
    for caso in casos:
        inicio = time.monotonic()
        resultado = {chave: caso[chave] for chave in ("id", "grupo", "perfil", "capacidade")}
        contexto = {"repositorio": RAIZ, "medidas": {}}
        cliente = None
        with tempfile.TemporaryDirectory(prefix="sls-homologacao-") as pasta:
            try:
                cliente = Cliente(comando, Path(pasta).resolve(), prazo=args.prazo)
                cliente.inicie()
                resultado["servidor"] = cliente.informacao
                if caso["capacidade"]:
                    cliente.exija(caso["capacidade"])
                caso["execute"](cliente, contexto)
                resultado.update(estado="OK", detalhe="comportamento conferido")
            except Pendente as erro:
                resultado.update(estado="PENDENTE", detalhe=str(erro))
            except Exception as erro:
                resultado.update(estado="FALHA", detalhe=f"{type(erro).__name__}: {erro}")
            finally:
                if cliente:
                    try:
                        cliente.feche()
                    except Exception as erro:
                        resultado.update(estado="FALHA", detalhe=resultado.get("detalhe", "") + f"; encerramento: {erro}")
                    if cliente.erros:
                        resultado["stderr"] = cliente.erros.decode("utf-8", errors="replace")
            resultado["duracao_ms"] = round((time.monotonic() - inicio) * 1000, 2)
            resultado["medidas"] = contexto["medidas"]
            resultados.append(resultado)
            print(f"[{resultado['estado']}] {caso['id']}: {resultado['detalhe']}", flush=True)
    resumo = estado(args.perfil, resultados, bool(args.caso))
    relatorio = {"formato": 1, "alvo": "SLS 1.0 — candidato, não publicado", "perfil": args.perfil,
                 "execucao_parcial": bool(args.caso), "procedencia": origem, "resumo": resumo,
                 "casos": resultados,
                 "gates_externos": [{"id": chave, "estado": "PENDENTE", "criterio": valor}
                                    for chave, valor in GATES_EXTERNOS.items()]}
    if args.relatorio:
        args.relatorio.parent.mkdir(parents=True, exist_ok=True)
        args.relatorio.write_text(json.dumps(relatorio, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Resumo: " + "; ".join(f"{chave}={valor}" for chave, valor in resumo["totais"].items()))
    if args.perfil == "1.0":
        print("SLS 1.0 NÃO liberado: o relatório não substitui os gates externos de homologação.")
    if args.caso:
        print("Execução parcial: não homologa o perfil completo.")
    return resumo["codigo_saida"]


if __name__ == "__main__":
    raise SystemExit(principal())
