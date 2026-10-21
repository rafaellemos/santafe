#!/usr/bin/env python3
"""Primeira etapa do SLS: intervalos do núcleo e espelho incremental UTF-16."""
from pathlib import Path
import random
import subprocess
import tempfile
import unittest

from sls.cliente import Cliente, posicao, recorte

RAIZ = Path(__file__).resolve().parents[2]
COMANDO = [str(RAIZ / "src/santafé"), str(RAIZ / "ferramentas/sls/sls.fé")]


def faixa(a, b, linha=0):
    return {"start": {"line": linha, "character": a}, "end": {"line": linha, "character": b}}


class Incremental(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory(prefix="sls-etapa1-")
        self.cliente = Cliente(COMANDO, Path(self.pasta.name).resolve())
        self.cliente.inicie()

    def tearDown(self):
        try:
            self.cliente.feche()
        finally:
            self.pasta.cleanup()

    def abrir(self, texto, nome="principal.fé"):
        uri = self.cliente.abra(texto, nome)
        self.cliente.diagnosticos(uri, 1)
        return uri

    def alterar(self, uri, versao, mudancas):
        self.cliente.notifique("textDocument/didChange", {
            "textDocument": {"uri": uri, "version": versao}, "contentChanges": mudancas})
        return self.cliente.diagnosticos(uri, versao)

    def barreira(self):
        self.assertEqual(self.cliente.solicite_bruto("santafe/teste-desconhecido")["error"]["code"], -32601)

    def test_anuncia_incremental(self):
        self.assertEqual(self.cliente.capacidades["textDocumentSync"]["change"], 2)
        self.assertEqual(self.cliente.informacao["version"], "1.0.0")

    def test_token_utf16(self):
        texto = 'local emoji = "🟢 é"; local índice = )\n'
        uri = self.cliente.abra(texto)
        erro = self.cliente.diagnosticos(uri, 1)[0]
        self.assertEqual(recorte(texto, erro["range"]), ")")
        self.assertEqual(erro["range"]["start"], posicao(texto, texto.index(")")))
        self.assertEqual(erro["code"], "sintaxe")

    def test_uri_com_dois_pontos_nao_define_a_linha(self):
        uri = self.cliente.abra("local x = 1\nlocal y = )", "uri:12: exemplo.fé")
        erro = self.cliente.diagnosticos(uri, 1)[0]
        self.assertEqual(erro["range"]["start"], {"line": 1, "character": 10})

    def test_diagnostico_multilinha(self):
        texto = "local x = [=[ação\n🟢"
        uri = self.cliente.abra(texto)
        erro = self.cliente.diagnosticos(uri, 1)[0]
        self.assertEqual(recorte(texto, erro["range"]), "[=[ação\n🟢")

    def test_fim_do_arquivo_vazio(self):
        texto = "se verdadeiro então\n"
        uri = self.cliente.abra(texto)
        erro = self.cliente.diagnosticos(uri, 1)[0]
        self.assertEqual(erro["range"], faixa(0, 0, 1))

    def test_substitui_emoji_sem_cortar_par(self):
        texto = 'local x = "🟢"; mostre(x)'
        uri = self.abrir(texto)
        self.assertEqual(self.alterar(uri, 2, [{"range": faixa(11, 13), "rangeLength": 2, "text": "á"}]), [])
        erros = self.alterar(uri, 3, [{"range": faixa(15, 21), "text": ")"}])
        self.assertEqual(erros[0]["range"], faixa(15, 16))

    def test_mudancas_sao_sequenciais(self):
        uri = self.abrir("local x = 1")
        erros = self.alterar(uri, 2, [
            {"range": faixa(10, 11), "text": "123"},
            {"range": faixa(13, 13), "text": " + )"},
        ])
        self.assertEqual(erros[0]["range"], faixa(16, 17))

    def test_texto_integral_e_incremental_no_mesmo_lote(self):
        uri = self.abrir("local x = 1")
        novo = "local índice = 2"
        p = len(novo.encode("utf-16-le")) // 2
        erros = self.alterar(uri, 2, [{"text": novo},
                                     {"range": faixa(p, p), "text": " + )"}])
        self.assertEqual(erros[0]["range"], faixa(p + 3, p + 4))

    def test_crlf(self):
        uri = self.abrir("local a = 1\r\nlocal b = 2\r\n")
        erro = self.alterar(uri, 2, [{"range": faixa(10, 11, 1), "text": ")"}])[0]
        self.assertEqual(erro["range"], faixa(10, 11, 1))
        self.assertEqual(self.alterar(uri, 3, [{"range": faixa(10, 11, 1), "text": "3"}]), [])

    def test_cr_isolado(self):
        uri = self.abrir("local a = 1\rlocal b = 2")
        erro = self.alterar(uri, 2, [{"range": faixa(10, 11, 1), "text": ")"}])[0]
        self.assertEqual(erro["range"], faixa(10, 11, 1))

    def test_lfcr_sao_duas_linhas_lsp(self):
        # O lexer aceita LFCR como uma quebra; LSP considera LF e CR separados.
        uri = self.abrir("local a = 1\n\rlocal b = 2")
        erro = self.alterar(uri, 2, [{"range": faixa(10, 11, 2), "text": ")"}])[0]
        self.assertEqual(erro["range"], faixa(10, 11, 2))

    def test_remove_intervalo_entre_linhas(self):
        uri = self.abrir("local a = 1\r\nlocal b = 2")
        self.assertEqual(self.alterar(uri, 2, [{"range": {"start": {"line": 0, "character": 10},
                                                                        "end": {"line": 1, "character": 11}},
                                                        "text": "3"}]), [])
        erro = self.alterar(uri, 3, [{"range": faixa(10, 11), "text": ")"}])[0]
        self.assertEqual(erro["range"], faixa(10, 11))

    def test_coluna_alem_da_linha_e_limitada(self):
        uri = self.abrir("local x = 1")
        erro = self.alterar(uri, 2, [{"range": faixa(500, 600), "text": " + )"}])[0]
        self.assertEqual(erro["range"], faixa(14, 15))

    def test_acento_combinado_nao_e_um_grafema_lsp(self):
        uri = self.abrir('local x = "é"; mostre(x)')
        self.assertEqual(self.alterar(uri, 2, [{"range": faixa(12, 13), "text": ""}]), [])
        erro = self.alterar(uri, 3, [{"range": faixa(15, 21), "text": ")"}])[0]
        self.assertEqual(erro["range"], faixa(15, 16))

    def test_intervalo_invalido_descarta_lote_e_exige_ressincronizacao(self):
        uri = self.abrir("local x = 1")
        self.assertEqual(self.alterar(uri, 2, [{"range": faixa(10, 11), "text": ")"},
                                             {"range": faixa(0, 1, 500), "text": "x"}]), [])
        aviso = self.cliente.receba(lambda m: m.get("method") == "window/logMessage")
        self.assertIn("texto integral", aviso["params"]["message"])
        # Não aceitar novo delta calculado sobre o estado divergente.
        self.assertEqual(self.alterar(uri, 3, [{"range": faixa(10, 11), "text": ")"}]), [])
        erros = self.alterar(uri, 4, [{"text": "local x = )"}])
        self.assertEqual(erros[0]["range"], faixa(10, 11))

    def test_recusa_metade_de_par_substituto(self):
        uri = self.abrir('local x = "🟢"')
        self.assertEqual(self.alterar(uri, 2, [{"range": faixa(12, 13), "text": "a"}]), [])
        aviso = self.cliente.receba(lambda m: m.get("method") == "window/logMessage")
        self.assertIn("par UTF-16", aviso["params"]["message"])
        self.assertEqual(self.alterar(uri, 3, [{"text": "local x = 3"}]), [])

    def test_range_length_incorreto_recusado(self):
        uri = self.abrir('local x = "🟢"')
        self.alterar(uri, 2, [{"range": faixa(11, 13), "rangeLength": 1, "text": "a"}])
        aviso = self.cliente.receba(lambda m: m.get("method") == "window/logMessage")
        self.assertIn("rangeLength", aviso["params"]["message"])

    def test_versao_antiga_duplicada_e_fracionaria_ignoradas(self):
        uri = self.abrir("local x = 1")
        self.alterar(uri, 3, [{"text": "local x = 3"}])
        for versao in (1, 3, 3.5):
            self.cliente.notifique("textDocument/didChange", {"textDocument": {"uri": uri, "version": versao},
                                                             "contentChanges": [{"text": "local x = )"}]})
        self.cliente.notifique("textDocument/didSave", {"textDocument": {"uri": uri}})
        self.assertEqual(self.cliente.diagnosticos(uri, 3), [])

    def test_notificacao_de_documento_fechado_nao_reabre(self):
        uri = self.abrir("local x = 1")
        self.cliente.notifique("textDocument/didClose", {"textDocument": {"uri": uri}})
        self.cliente.diagnosticos(uri)
        self.cliente.notifique("textDocument/didSave", {"textDocument": {"uri": uri}, "text": "local x = )"})
        self.cliente.notifique("textDocument/didChange", {"textDocument": {"uri": uri, "version": 2},
                                                         "contentChanges": [{"text": "local x = )"}]})
        self.barreira()
        self.assertFalse(any(m.get("method") == "textDocument/publishDiagnostics" for m in self.cliente.pendentes))
        self.cliente.abra("local x = 1")
        self.assertEqual(self.cliente.diagnosticos(uri, 1), [])

    def test_didopen_duplicado_nao_sobrescreve(self):
        uri = self.abrir("local x = 1")
        self.cliente.notifique("textDocument/didOpen", {"textDocument": {"uri": uri, "version": 2, "text": "local x = )"}})
        self.cliente.notifique("textDocument/didSave", {"textDocument": {"uri": uri}})
        self.assertEqual(self.cliente.diagnosticos(uri, 1), [])

    def test_lote_excessivo_ressincroniza(self):
        uri = self.abrir("local x = 1")
        self.assertEqual(self.alterar(uri, 2, [{"text": "local x = 2"}] * 257), [])
        aviso = self.cliente.receba(lambda m: m.get("method") == "window/logMessage")
        self.assertIn("excessiva", aviso["params"]["message"])
        self.assertEqual(self.alterar(uri, 3, [{"text": "local x = 3"}]), [])

    def test_documento_excessivo_recusado(self):
        uri = self.abrir("local x = 1")
        self.assertEqual(self.alterar(uri, 2, [{"text": " " * (4 * 1024 * 1024 + 1)}]), [])
        aviso = self.cliente.receba(lambda m: m.get("method") == "window/logMessage")
        self.assertIn("4 MiB", aviso["params"]["message"])

    def test_nucleo_antigo_falha_explicita(self):
        # Simula núcleo sem a API nova usando o binário de teste, não o instalado.
        # Framing gerado pelo helper para evitar fixture com comprimento errado.
        from sls.cliente import quadro, leia_quadro
        import io
        processo = subprocess.run(COMANDO[:1] + ["-e", "depure.analise = nulo", COMANDO[1]],
                                  input=quadro({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
                                  capture_output=True, timeout=5)
        self.assertEqual(leia_quadro(io.BytesIO(processo.stdout))["error"]["code"], -32603)

    def test_100_edicoes_diferenciais(self):
        texto = 'local x = "🟢 é"\nmostre(x)\n'
        uri = self.abrir(texto)
        referencia = Cliente(COMANDO, self.cliente.raiz)
        referencia.inicie()
        try:
            referencia.abra(texto)
            referencia.diagnosticos(uri, 1)
            sorteio = random.Random(20261021)
            fragmentos = ["é", "é", "🟢", "\n", "\r\n", "--", "[[", "]]", "®", "Ⓡ", "local ", ")", "fim", " ", ""]
            for versao in range(2, 102):
                limites = [i for i in range(len(texto) + 1) if not (0 < i < len(texto) and texto[i - 1:i + 1] == "\r\n")]
                a, b = sorted(sorteio.sample(limites, 2)) if len(limites) > 1 else (0, 0)
                novo = sorteio.choice(fragmentos)
                mudanca = {"range": {"start": posicao(texto, a), "end": posicao(texto, b)}, "text": novo}
                texto = texto[:a] + novo + texto[b:]
                incremental = self.alterar(uri, versao, [mudanca])
                referencia.notifique("textDocument/didChange", {"textDocument": {"uri": uri, "version": versao},
                                                                "contentChanges": [{"text": texto}]})
                self.assertEqual(incremental, referencia.diagnosticos(uri, versao), f"edição {versao}: {texto!r}")
        finally:
            referencia.feche()


if __name__ == "__main__":
    unittest.main(verbosity=2)
