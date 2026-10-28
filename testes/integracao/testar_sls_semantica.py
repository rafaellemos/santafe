"""Casos adversariais independentes da bateria de aceitação principal."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from sls.cliente import Cliente, aplique_edicoes, edicoes_por_uri, posicao

ROOT = Path(__file__).resolve().parents[2]
COMMAND = [str(ROOT / 'src/santafé'), str(ROOT / 'ferramentas/sls/sls.fé')]


class Semantica(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='sls-semantica-')
        self.root = Path(self.tmp.name).resolve()
        self.c = Cliente(COMMAND, self.root)
        self.c.inicie()

    def tearDown(self):
        try:
            self.c.feche()
        finally:
            self.tmp.cleanup()

    def rename(self, text, old, new, index=0):
        uri = self.c.abra(text)
        params = self.c.no_ponto(uri, text, old, dentro=index)
        params['newName'] = new
        return uri, self.c.solicite_bruto('textDocument/rename', params)

    def test_nfc_nfd_distintos(self):
        text = 'local variável, variável=1,2; mostre(`®variávelⓇvariável ®{variável+variável}`)'
        uri, response = self.rename(text, 'variável', 'posição')
        edits = edicoes_por_uri(response['result'])
        self.assertEqual(aplique_edicoes(text, edits[uri]), text.replace('variável', 'posição'))

    def test_parametros_invalidos_sao_invalid_params(self):
        text='local x=1; mostre(x)'; uri=self.c.abra(text)
        td={'textDocument':{'uri':uri}}
        cases=[('textDocument/definition',{}),
               ('textDocument/hover',{**td,'position':False}),
               ('textDocument/hover',{**td,'position':{'line':-1,'character':0}}),
               ('textDocument/hover',{**td,'position':{'line':0,'character':0.5}}),
               ('workspace/symbol',{'query':{}}),
               ('textDocument/rename',{**td,'position':{'line':0,'character':6},'newName':42}),
               ('textDocument/formatting',{**td,'options':{'tabSize':'2','insertSpaces':True}}),
               ('textDocument/references',{**td,'position':{'line':0,'character':6},'context':False}),
               ('textDocument/selectionRange',{**td,'positions':[False]}),
               ('textDocument/codeAction',{**td,'range':{}})]
        for method,params in cases:
            response=self.c.solicite_bruto(method,params)
            self.assertEqual(response.get('error',{}).get('code'),-32602,response)
        self.assertTrue(self.c.solicite('textDocument/documentSymbol',td))

    def test_colisao_local(self):
        _, response = self.rename('local x=1; local y=2; mostre(x+y)', 'x', 'y')
        self.assertIn('error', response)

    def test_captura_global(self):
        _, response = self.rename('local x=1; mostre(x,y)', 'x', 'y')
        self.assertIn('error', response)

    def test_colisao_em_escopo_interno(self):
        _, response = self.rename('local x=1; início local y=2; mostre(x,y) fim', 'x', 'y')
        self.assertIn('error', response)

    def test_colar_com_escape_na_expressao_recusado(self):
        _, response = self.rename('local x=1; mostre(`®{x .. \\"a\\"}`)', 'x', 'y')
        self.assertIn('error', response)

    def test_import_reassigned_recusado(self):
        (self.root/'m.fé').write_text('local M={}; função M.f() fim; retorne M')
        text = 'local M=importe "m"; M=outro(); M.f()'
        uri = self.c.abra(text)
        value = self.c.solicite('textDocument/definition', self.c.no_ponto(uri,text,'f()',dentro=0))
        self.assertIsNone(value)

    def test_symlink_arquivo_nao_lido(self):
        with tempfile.TemporaryDirectory() as outside:
            target=Path(outside)/'fora.fé'
            target.write_text('local M={}; função M.segredo() fim; retorne M')
            (self.root/'fora.fé').symlink_to(target)
            text='local F=importe "fora"; F.'
            uri=self.c.abra(text)
            items=self.c.solicite('textDocument/completion',self.c.no_ponto(uri,text,'F.',dentro=2))
            self.assertNotIn('segredo',{i['label'] for i in items})

    def test_symlink_diretorio_nao_lido(self):
        with tempfile.TemporaryDirectory() as outside:
            (Path(outside)/'mod.fé').write_text('local M={}; função M.segredo() fim; retorne M')
            (self.root/'fora').symlink_to(outside,target_is_directory=True)
            text='local F=importe "fora.mod"; F.'
            uri=self.c.abra(text)
            items=self.c.solicite('textDocument/completion',self.c.no_ponto(uri,text,'F.',dentro=2))
            self.assertNotIn('segredo',{i['label'] for i in items})

    def test_importacao_ciclica_nao_bloqueia(self):
        (self.root/'a.fé').write_text('local B=importe "b"; local M={}; função M.f() fim; retorne M')
        (self.root/'b.fé').write_text('local A=importe "a"; retorne A')
        text='local A=importe "a"; A.'
        uri=self.c.abra(text)
        items=self.c.solicite('textDocument/completion',self.c.no_ponto(uri,text,'A.',dentro=2))
        self.assertIn('f',{i['label'] for i in items})

    def test_campos_dinamicos_recusa_rename(self):
        text='local M={}; M["f"]=função() fim; M.f()'
        uri=self.c.abra(text)
        p=self.c.no_ponto(uri,text,'M.f',dentro=2); p['newName']='g'
        value=self.c.solicite_bruto('textDocument/rename',p)
        self.assertTrue('error' in value or value.get('result') is None)

    def test_formatar_preserva_interior_literal_e_comentario(self):
        text='local função f()\nlocal x=[=[a\n  b\n c]=]\n--[=[oi\n  interno\n]=]\nretorne x\nfim\n'
        literal='[=[a\n  b\n c]=]'
        if 'dados.' in self.c.informacao.get('version',''):
            text=text.replace(literal,'[=[a\n  b\n c]=]'); literal='[=[a\n  b\n c]=]'
        uri=self.c.abra(text)
        params={'textDocument':{'uri':uri},'options':{'tabSize':2,'insertSpaces':True}}
        edits=self.c.solicite('textDocument/formatting',params)
        new=aplique_edicoes(text,edits)
        self.assertIn(literal,new)
        self.assertIn('--[=[oi\n  interno\n]=]',new)
        self.assertIn('\n  retorne x',new)
        self.c.mude(uri,new)
        self.assertEqual(self.c.diagnosticos(uri,2),[])
        self.assertEqual(self.c.solicite('textDocument/formatting',params),[])

    def test_complecao_nao_aparece_dentro_de_colar(self):
        text='local s="tabela."'
        uri=self.c.abra(text)
        items=self.c.solicite('textDocument/completion',self.c.no_ponto(uri,text,'tabela.',dentro=7))
        self.assertEqual(items,[])

    def test_corpus_real(self):
        files=[]
        for base in ('bibs','ferramentas','aplicativos'):
            files.extend(str(p) for p in (ROOT/base).rglob('*.fé') if p.is_file())
        result=subprocess.run([os.environ.get('SANTAFE_ESTAVEL',str(ROOT/'src/santafé')),str(ROOT/'testes/integracao/sls/corpus.fé'),
                               str(ROOT/'ferramentas/sls/analisador.fé')],
                              input=json.dumps(files),text=True,capture_output=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout),[])

    def test_indice_inclui_consumidor_fechado_e_percentual_no_caminho(self):
        module='local M={}; função M.somar(a,b) retorne a+b fim; retorne M'
        consumer='local M=importe "modulo"; mostre(M.somar(1,2))'
        (self.root/'modulo.fé').write_text(module)
        closed=self.root/'consumidor 100%.fé'
        closed.write_text(consumer)
        uri=self.c.abra(module,'modulo.fé')
        p=self.c.no_ponto(uri,module,'somar'); p['newName']='somatório'
        reply=self.c.solicite_bruto('textDocument/rename',p)
        self.assertIn('result',reply)
        edits=edicoes_por_uri(reply['result'])
        self.assertIn(closed.as_uri(),edits)
        self.assertEqual(aplique_edicoes(consumer,edits[closed.as_uri()]),consumer.replace('somar','somatório'))
        closed_edit=next(d for d in reply['result']['documentChanges'] if d['textDocument']['uri']==closed.as_uri())
        self.assertIsNone(closed_edit['textDocument']['version'])
        self.assertEqual(closed.read_text(),consumer, 'SLS não grava o arquivo')

    def test_simbolos_fechados_e_diretorios_ignorados(self):
        (self.root/'fechado.fé').write_text('local função fechado() fim')
        (self.root/'node_modules').mkdir()
        (self.root/'node_modules/oculto.fé').write_text('local segredo=1')
        result=self.c.solicite('workspace/symbol',{'query':''})
        self.assertIn('fechado',{s['name'] for s in result})
        self.assertNotIn('segredo',{s['name'] for s in result})

    def test_limite_indice_recusa_rename_parcial(self):
        for i in range(513):
            (self.root/f'fonte{i:04}.fé').write_text('local x=1')
        _,reply=self.rename('local M={}; função M.campo() fim; M.campo()','campo','novo')
        self.assertIn('error',reply)
        self.assertIn('índice incompleto',reply['error']['message'])

    def test_local_nao_depende_do_tamanho_do_projeto(self):
        for i in range(513):
            (self.root/f'fonte{i:04}.fé').write_text('local x=1')
        uri,reply=self.rename('local x=1; mostre(x)','x','y')
        self.assertEqual(set(edicoes_por_uri(reply['result'])),{uri})

    def test_global_dinamico_nao_oferece_rename_parcial(self):
        text='função global() fim; global(); _G["global"]()'
        uri=self.c.abra(text)
        p=self.c.no_ponto(uri,text,'global')
        self.assertIsNone(self.c.solicite('textDocument/prepareRename',p))
        p['newName']='outro'
        self.assertIn('error',self.c.solicite_bruto('textDocument/rename',p))

    def test_alteracao_de_raizes_e_isolamento(self):
        with tempfile.TemporaryDirectory(prefix='sls-outra-raiz-') as temp:
            other=Path(temp).resolve()
            (other/'m.fé').write_text('local M={}; função M.outra() fim; retorne M')
            (self.root/'m.fé').write_text('local M={}; função M.primeira() fim; retorne M')
            self.c.notifique('workspace/didChangeWorkspaceFolders',{'event':{
                'added':[{'uri':other.as_uri(),'name':'outra'}],'removed':[]}})
            text='local M=importe "m"; M.'
            for path,expected,absent in ((self.root/'a.fé','primeira','outra'),(other/'a.fé','outra','primeira')):
                uri=self.c.abra(text,str(path))
                names={i['label'] for i in self.c.solicite('textDocument/completion',self.c.no_ponto(uri,text,'M.',dentro=2))}
                self.assertIn(expected,names); self.assertNotIn(absent,names)
            self.c.notifique('workspace/didChangeWorkspaceFolders',{'event':{'added':[],
                'removed':[{'uri':other.as_uri(),'name':'outra'}]}})
            names={i['label'] for i in self.c.solicite('textDocument/completion',self.c.no_ponto(uri,text,'M.',dentro=2))}
            self.assertNotIn('outra',names)

    def test_watcher_invalida_modulo_fechado(self):
        module=self.root/'m.fé'
        module.write_text('local M={}; função M.antes() fim; retorne M')
        text='local M=importe "m"; M.'; uri=self.c.abra(text)
        p=self.c.no_ponto(uri,text,'M.',dentro=2)
        self.assertIn('antes',{i['label'] for i in self.c.solicite('textDocument/completion',p)})
        module.write_text('local M={}; função M.depois() fim; retorne M')
        self.c.notifique('workspace/didChangeWatchedFiles',{'changes':[{'uri':module.as_uri(),'type':2}]})
        names={i['label'] for i in self.c.solicite('textDocument/completion',p)}
        self.assertIn('depois',names); self.assertNotIn('antes',names)

    def test_fifo_nao_bloqueia_indice(self):
        import os
        os.mkfifo(self.root/'fifo.fé')
        self.assertEqual(self.c.solicite('workspace/symbol',{'query':''}),[])

    def test_alias_e_indice_recusam_rename_de_campo(self):
        for suffix in ('local N=M; N.f()', 'M["f"]()', 'desconhecido(M)'):
            text='local M={}; função M.f() fim; '+suffix
            uri=self.c.abra(text)
            p=self.c.no_ponto(uri,text,'M.f',dentro=2); p['newName']='g'
            self.assertIn('error',self.c.solicite_bruto('textDocument/rename',p))
            self.c.notifique('textDocument/didClose',{'textDocument':{'uri':uri}})

    def test_diagnosticos_multiplos_e_correcao(self):
        text='local a = ;\nlocal b = ;\nlocal c = 3'
        uri=self.c.abra(text)
        errors=self.c.diagnosticos(uri,1)
        self.assertGreaterEqual(len(errors),2)
        self.assertTrue({0,1}.issubset({e['range']['start']['line'] for e in errors}))
        self.c.mude(uri,'local a,b,c=1,2,3')
        self.assertEqual(self.c.diagnosticos(uri,2),[])


if __name__=='__main__':
    unittest.main(verbosity=2)
