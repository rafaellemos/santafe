#!/usr/bin/env python3
"""Integração do dialeto candidato; nenhum fonte editado é executado pelo SLS."""
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'testes/integracao'))
from sls.cliente import Cliente, aplique_edicoes, posicao
import testar_sls_semantica as semantica
import testar_sls_cancelamento as transporte
COMMAND=[os.environ.get('SANTAFE_CANDIDATO',str(ROOT/'dist/candidato-dados-v2/santafé-dados')),
         '-E','-P',str(ROOT/'ferramentas/sls/sls.fé')]

class Dados(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='sls-dados2-')
        self.root=Path(self.tmp.name).resolve()
        self.c=Cliente(COMMAND,self.root)
        original=self.c.solicite
        def request(method, params=None):
            if method=='initialize': params={**params,'initializationOptions':{'avisosEscopo':True}}
            return original(method,params)
        self.c.solicite=request
        self.c.inicie()
    def tearDown(self):
        try: self.c.feche()
        finally: self.tmp.cleanup()
    def test_lista_nulo_e_apis(self):
        text='local var\nlocal l=[var,nulo,[],{}]\nlocal t={a=nulo}\nmostre(tabela.temChave(t,"a"),#l)\ntabela.'
        uri=self.c.abra(text)
        self.assertTrue(self.c.diagnosticos(uri,1)) # ponto final intencionalmente incompleto
        labels={x['label'] for x in self.c.solicite('textDocument/completion',self.c.no_ponto(uri,text,'tabela.',ultimo=True,dentro=7))}
        self.assertTrue({'temChave','apague'} <= labels,labels)
        self.assertNotIn('temVar',labels)
        valid=text[:-7]
        self.c.mude(uri,valid)
        self.assertEqual(self.c.diagnosticos(uri,2),[])
    def test_lexer_nome_longo_ancorado_durante_gc(self):
        source='''coleteLixo("definaPausa",200); coleteLixo("definaMultiplicadorDoPasso",200)
local texto=("a={x=1,y=2};"):replique(20000)
para i=1,12 início
  coleteLixo("colete")
  local nome="@/" .. ("caminho-longo/"):replique(15) .. paraColar(i) .. ".fé"
  local tokens, falha=depure.lexemas(texto,nome,10000)
  garanta(falha e falha.código=="limite-lexemas")
  garanta(#tokens==10000)
fim
mostre("LEXEMAS_NOME_ANCorado_OK")'''
        p=subprocess.run([COMMAND[0],'-E','-P','-e',source],capture_output=True,text=True,timeout=30)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        self.assertNotIn('Sanitizer',p.stderr)
    def test_escopo_nao_confunde_nulo_com_ausencia(self):
        text='local var\nlocal outra=nulo\nmostre(var,outra,naoDeclarada)'
        uri=self.c.abra(text); ds=self.c.diagnosticos(uri,1)
        self.assertEqual(len(ds),1,ds)
        self.assertEqual(ds[0]['code'],'nome-sem-declaração-local')
        self.assertEqual(ds[0]['severity'],2)
        self.assertIn('naoDeclarada',ds[0]['message'])
        self.assertEqual(ds[0]['range']['start'],posicao(text,text.index('naoDeclarada')))
        self.c.mude(uri,'local naoDeclarada=nulo\n'+text)
        self.assertEqual(self.c.diagnosticos(uri,2),[])
    def test_escopo_e_sombra(self):
        text='local x=nulo\ninício local x=1; mostre(x) fim\nmostre(x)\ninício local interna=1 fim\nmostre(interna)'
        uri=self.c.abra(text); ds=self.c.diagnosticos(uri,1)
        self.assertEqual(len(ds),1,ds); self.assertIn('interna',ds[0]['message'])
    def test_onfe_nao_compila_e_incremental(self):
        text='{lista=[nulo,{},[]], [1]="um", ["1"]="texto"}'
        uri=self.c.abra(text,'exemplo.onfé')
        self.assertEqual(self.c.diagnosticos(uri,1),[])
        self.c.mude(uri,'{lista=[nulo,]}')
        self.assertEqual(self.c.diagnosticos(uri,2),[]) # vírgula final é dado válido
        self.c.mude(uri,'{x=(função() so.execute("crie-nao") fim)()}')
        self.assertTrue(self.c.diagnosticos(uri,3))
        self.assertFalse((self.root/'crie-nao').exists())
        self.c.mude(uri,'{x=nulo}')
        self.assertEqual(self.c.diagnosticos(uri,4),[])
        td={'textDocument':{'uri':uri}}
        self.assertEqual(self.c.solicite('textDocument/documentSymbol',td),[])
        self.assertEqual(self.c.solicite('textDocument/semanticTokens/full',td),{'data':[]})
        self.assertEqual(self.c.solicite('textDocument/formatting',{**td,'options':{'tabSize':2,'insertSpaces':True}}),[])
    def test_onfe_diagnostico_unicode(self):
        text='{nome="José 👩🏽‍💻",nome="duplicado"}'
        uri=self.c.abra(text,'erro.onfé'); ds=self.c.diagnosticos(uri,1)
        self.assertEqual(len(ds),1)
        self.assertIn('duplic',ds[0]['message'])
        self.assertGreater(ds[0]['range']['start']['character'],10)
    def test_onfe_sem_nome_no_sublime(self):
        uri='buffer:42'
        self.c.notifique('textDocument/didOpen', {'textDocument':{
            'uri':uri,'languageId':'onfe','version':0,'text':'{lista=[nulo],tabela={}}'}})
        self.assertEqual(self.c.diagnosticos(uri,0),[])
        self.c.notifique('textDocument/didChange', {'textDocument':{'uri':uri,'version':1},
            'contentChanges':[{'text':'importe "nao-execute"'}]})
        self.assertTrue(self.c.diagnosticos(uri,1))
        self.c.notifique('textDocument/didClose', {'textDocument':{'uri':uri}})
        self.assertEqual(self.c.diagnosticos(uri),[])
    def test_fecha_reabre_sem_cache_obsoleto(self):
        for i in range(25):
            text=f'local valor{i}=[nulo]; mostre(valor{i})'
            uri=self.c.abra(text)
            self.assertEqual(self.c.diagnosticos(uri,1),[])
            syms=self.c.solicite('textDocument/documentSymbol',{'textDocument':{'uri':uri}})
            self.assertEqual([s['name'] for s in syms],[f'valor{i}'])
            self.c.notifique('textDocument/didClose',{'textDocument':{'uri':uri}})
            self.assertEqual(self.c.diagnosticos(uri),[])
    def test_rename_gabaritos_nao_bruto_com_lista(self):
        text='local variável=[nulo]; local bruto=[=[®variável]=]; mostre(`®variável Ⓡ{variável[1]}`)'
        uri=self.c.abra(text); self.assertEqual(self.c.diagnosticos(uri,1),[])
        response=self.c.solicite('textDocument/rename',{**self.c.no_ponto(uri,text,'variável'),'newName':'outra'})
        changed=aplique_edicoes(text,response['documentChanges'][0]['edits'])
        self.assertIn('[=[®variável]=]',changed)
        self.assertIn('`®outra Ⓡ{outra[1]}`',changed)
    def test_formatacao_dialeto_idempotente(self):
        text='local função f()\nlocal l=[1, [nulo,2]]\nlocal r=[=[a\n  b\n c]=]\nretorne l,r\nfim\n'
        uri=self.c.abra(text); self.assertEqual(self.c.diagnosticos(uri,1),[])
        params={'textDocument':{'uri':uri},'options':{'tabSize':2,'insertSpaces':True}}
        changed=aplique_edicoes(text,self.c.solicite('textDocument/formatting',params))
        self.assertIn('[=[a\n  b\n c]=]',changed)
        self.c.mude(uri,changed); self.assertEqual(self.c.diagnosticos(uri,2),[])
        self.assertEqual(self.c.solicite('textDocument/formatting',params),[])

if __name__=='__main__':
    semantica.COMMAND=transporte.COMMAND=COMMAND
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(Dados))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(semantica))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(transporte))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(not result.wasSuccessful())
