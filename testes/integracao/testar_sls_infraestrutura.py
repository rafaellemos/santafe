#!/usr/bin/env python3
"""Autotestes do verificador: não permitir falsos positivos no contrato 1.0."""
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

from sls.cliente import (Cliente, FalhaLsp, aplique_edicoes, deslocamento, edicoes_por_uri,
                        leia_quadro, posicao, quadro, recorte)
from sls.casos import CASOS
from testar_sls_aceitacao import estado


def intervalo(a, b):
    return {"start": {"line": 0, "character": a}, "end": {"line": 0, "character": b}}


class Infraestrutura(unittest.TestCase):
    def test_quadro_utf8(self):
        mensagem = {"jsonrpc": "2.0", "id": 1, "result": "ação 🟢"}
        self.assertEqual(leia_quadro(io.BytesIO(quadro(mensagem))), mensagem)

    def test_duas_respostas(self):
        a = {"jsonrpc": "2.0", "id": 1, "result": None}
        b = {"jsonrpc": "2.0", "id": 2, "result": []}
        stream = io.BytesIO(quadro(a) + quadro(b))
        self.assertEqual(leia_quadro(stream), a)
        self.assertEqual(leia_quadro(stream), b)

    def test_quadro_invalido_nao_passa(self):
        for dados in [b"log solto\n", b"X: 1\r\n\r\n", b"Content-Length: 2\r\n\r\n{",
                      b"Content-Length: 16777217\r\n\r\n", b"x" * 8193,
                      b"Content-Length: 1\r\nContent-Length: 1\r\n\r\n0",
                      b"Content-Length: 1\r\n\r\n\xff", b"Content-Length: 1\r\n\r\n{",
                      b"Content-Length: 2\r\n\r\n[]"]:
            with self.subTest(dados=dados[:60]):
                with self.assertRaises(FalhaLsp):
                    leia_quadro(io.BytesIO(dados))

    def test_posicoes_utf16(self):
        texto = "🟢 é\r\níndice\n"
        for indice in (0, 1, 2, 3, 4, 6, 7, len(texto)):
            self.assertEqual(deslocamento(texto, posicao(texto, indice)), indice)
        self.assertEqual(posicao(texto, 1), {"line": 0, "character": 2})
        with self.assertRaises(FalhaLsp):
            deslocamento(texto, {"line": 0, "character": 1})
        with self.assertRaises(FalhaLsp):
            deslocamento(texto, {"line": 10, "character": 0})
        with self.assertRaises(FalhaLsp):
            deslocamento(texto, {"line": 0, "character": 200})

    def test_rename_utf16(self):
        texto = "🟢 nome nome"
        edicoes = [{"range": intervalo(3, 7), "newText": "índice"},
                   {"range": intervalo(8, 12), "newText": "índice"}]
        self.assertEqual(aplique_edicoes(texto, edicoes), "🟢 índice índice")
        self.assertEqual(recorte(texto, intervalo(3, 7)), "nome")

    def test_edicoes_sobrepostas_recusadas(self):
        for intervalos in [(intervalo(0, 3), intervalo(2, 4)), (intervalo(0, 0), intervalo(0, 1))]:
            with self.assertRaises(FalhaLsp):
                aplique_edicoes("teste", [{"range": item, "newText": "x"} for item in intervalos])

    def test_intervalo_invertido_recusado(self):
        with self.assertRaises(FalhaLsp):
            aplique_edicoes("teste", [{"range": intervalo(3, 1), "newText": "x"}])

    def test_workspace_edit_aceita_duas_formas(self):
        uri = "file:///teste.fé"
        edicoes = [{"range": intervalo(0, 0), "newText": "x"}]
        self.assertEqual(edicoes_por_uri({"changes": {uri: edicoes}}), {uri: edicoes})
        self.assertEqual(edicoes_por_uri({"documentChanges": [
            {"textDocument": {"uri": uri, "version": 1}, "edits": edicoes}]}), {uri: edicoes})

    def test_rename_nao_remove_arquivo(self):
        with self.assertRaises(FalhaLsp):
            edicoes_por_uri({"documentChanges": [{"kind": "delete", "uri": "file:///teste.fé"}]})

    def test_contrato_nao_conta_pendencia_como_ok(self):
        resumo = estado("1.0", [{"estado": "OK"}, {"estado": "PENDENTE"}])
        self.assertEqual(resumo["totais"], {"OK": 1, "FALHA": 0, "PENDENTE": 1})
        self.assertEqual(resumo["codigo_saida"], 2)
        self.assertFalse(resumo["liberavel_como_1_0"])

    def test_verde_automatizado_nao_atesta_editor_real(self):
        resumo = estado("1.0", [{"estado": "OK"}])
        self.assertEqual(resumo["codigo_saida"], 0)
        self.assertTrue(resumo["automacao_alvo_aprovada"])
        self.assertFalse(resumo["liberavel_como_1_0"])

    def test_falha_nao_e_pendente(self):
        self.assertEqual(estado("1.0", [{"estado": "FALHA"}])["codigo_saida"], 1)

    def test_base_verde(self):
        self.assertTrue(estado("atual", [{"estado": "OK"}])["perfil_atual_aprovado"])
        self.assertFalse(estado("atual", [{"estado": "OK"}], parcial=True)["perfil_atual_aprovado"])

    def test_ids_unicos_e_capacidades_declaradas(self):
        self.assertEqual(len(CASOS), len({item["id"] for item in CASOS}))
        for item in CASOS:
            self.assertIn(item["perfil"], ("atual", "1.0"))
            self.assertTrue(callable(item["execute"]))

    def test_timeout_e_limpeza_de_processo(self):
        with tempfile.TemporaryDirectory() as pasta:
            cliente = Cliente([sys.executable, "-c", "import time; time.sleep(300)"],
                              Path(pasta), prazo=0.1)
            try:
                with self.assertRaisesRegex(FalhaLsp, "prazo excedido"):
                    cliente.inicie()
            finally:
                cliente.feche()
            self.assertIsNotNone(cliente.processo.poll())
            self.assertFalse(cliente.leitor.is_alive())

    def test_anunciar_sem_implementar_nao_passa(self):
        class ServidorFalso:
            def abra(self, texto):
                return "file:///principal.fé"
            def no_ponto(self, *args, **kwargs):
                return {}
            def solicite(self, *args, **kwargs):
                return []
        caso = next(item for item in CASOS if item["id"] == "conclusao-de-globais")
        with self.assertRaisesRegex(FalhaLsp, "mostre ausente"):
            caso["execute"](ServidorFalso(), {})

    def test_fixture_da_biblioteca_fe_existe(self):
        raiz = Path(__file__).resolve().parents[2]
        dados = json.loads((raiz / "extensões/vscode/api-publica.json").read_text())
        self.assertTrue(any(item["rótulo"].startswith("correio.imap.") for item in dados["itens"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
