"""Cancelamento concorrente real, framing fragmentado e sobrevivência do host."""
from pathlib import Path
import tempfile
import time
import unittest

from sls.cliente import Cliente, quadro

ROOT = Path(__file__).resolve().parents[2]
COMMAND = [str(ROOT/'src/santafé'), str(ROOT/'ferramentas/sls/sls.fé')]


class Transporte(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='sls-transporte-')
        self.c = Cliente(COMMAND, Path(self.tmp.name).resolve(), prazo=8)
        self.c.inicie()

    def tearDown(self):
        try:
            self.c.feche()
        finally:
            self.tmp.cleanup()

    def confirme_vivo(self):
        uri = self.c.abra('local maçã=42\nmostre(maçã)', 'vivo.fé')
        self.assertEqual(self.c.diagnosticos(uri, 1), [])
        result = self.c.solicite('textDocument/documentSymbol', {'textDocument': {'uri':uri}})
        self.assertIn('maçã', {s['name'] for s in result})

    def test_cancelar_durante_analise_e_repetir(self):
        text = '\n'.join('global%d = {campo=1, outro=2}' % i for i in range(10000))
        uri = self.c.abra(text)
        self.assertEqual(self.c.diagnosticos(uri, 1), [])
        self.c.envie({'jsonrpc':'2.0','id':'longo','method':'textDocument/documentSymbol',
                      'params':{'textDocument':{'uri':uri}}})
        # Não está no mesmo lote: chega depois de o servidor começar o pedido.
        time.sleep(0.025)
        self.c.notifique('$/cancelRequest', {'id':'longo'})
        reply = self.c.receba(lambda m: m.get('id')=='longo')
        self.assertEqual(reply.get('error',{}).get('code'), -32800, reply)
        self.confirme_vivo()

    def test_cancelamento_enfileirado(self):
        uri = self.c.abra('local x=1')
        self.c.diagnosticos(uri,1)
        data = quadro({'jsonrpc':'2.0','id':'fila','method':'textDocument/documentSymbol',
                       'params':{'textDocument':{'uri':uri}}})
        data += quadro({'jsonrpc':'2.0','method':'$/cancelRequest','params':{'id':'fila'}})
        self.c.processo.stdin.write(data)
        self.c.processo.stdin.flush()
        reply = self.c.receba(lambda m: m.get('id')=='fila')
        self.assertEqual(reply.get('error',{}).get('code'),-32800,reply)
        self.confirme_vivo()

    def test_fragmentos_incluem_utf8_cortado(self):
        message = quadro({'jsonrpc':'2.0','id':'fragmentação','method':'workspace/symbol',
                          'params':{'query':'índice'}})
        for byte in message:
            self.c.processo.stdin.write(bytes([byte]))
            self.c.processo.stdin.flush()
        reply = self.c.receba(lambda m: m.get('id')=='fragmentação')
        self.assertIn('result',reply)
        self.confirme_vivo()

    def test_ids_invalidos_nao_encerram(self):
        for identity in ({'a':1}, [1], True):
            self.c.envie({'jsonrpc':'2.0','id':identity,'method':'workspace/symbol','params':{}})
            reply=self.c.receba(lambda m: m.get('error',{}).get('code')==-32600)
            self.assertIsNone(reply.get('id'))
        self.confirme_vivo()

    def test_erro_do_provedor_desarma_gancho(self):
        uri=self.c.abra('local x=1')
        self.c.diagnosticos(uri,1)
        for _ in range(30):
            self.c.solicite_bruto('textDocument/selectionRange',
                                 {'textDocument':{'uri':uri},'positions':[False]})
        self.confirme_vivo()


if __name__=='__main__':
    unittest.main(verbosity=2)
