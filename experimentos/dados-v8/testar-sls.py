#!/usr/bin/env python3
"""Mudanças incrementais de delimitador em código e ONFÉ, por LSP real."""
from pathlib import Path
import sys, tempfile
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'testes/integracao'))
from sls.cliente import Cliente,posicao,aplique_edicoes
with tempfile.TemporaryDirectory(prefix='sls-dados8-') as tmp:
    c=Cliente([str(ROOT/'src/santafé'),'-E','-P',str(ROOT/'ferramentas/sls/sls.fé')],Path(tmp))
    try:
        c.inicie()
        for ext,text in [('fé','local nome="José"\nlocal bruto=[=[🟢 ®nome Ⓡ{nome}\nsegunda linha]=]\nmostre(`®nome`)'),
                         ('onfé','{nome="José",bruto=[=[🟢 ®nome\nsegunda linha]=],lista=[[nulo],[]]}')]:
            uri=c.abra(text,'dados.'+ext); assert not c.diagnosticos(uri,1)
            # Uma única inserção no fechamento deixa os níveis diferentes.
            index=text.index(']=]')+1
            c.notifique('textDocument/didChange',{'textDocument':{'uri':uri,'version':2},'contentChanges':[
                {'range':{'start':posicao(text,index),'end':posicao(text,index)},'text':'='}]})
            broken=text[:index]+'='+text[index:]
            assert c.diagnosticos(uri,2)
            # Corrigir apenas a abertura restaura análise sem reabrir documento.
            index=broken.index('[=[')+1
            c.notifique('textDocument/didChange',{'textDocument':{'uri':uri,'version':3},'contentChanges':[
                {'range':{'start':posicao(broken,index),'end':posicao(broken,index)},'text':'='}]})
            fixed=broken[:index]+'='+broken[index:]
            assert not c.diagnosticos(uri,3)
            if ext=='fé':
                changes=c.solicite('textDocument/rename',{**c.no_ponto(uri,fixed,'nome'),'newName':'pessoa'})
                renamed=aplique_edicoes(fixed,changes['documentChanges'][0]['edits'])
                assert '[==[🟢 ®nome Ⓡ{nome}\nsegunda linha]==]' in renamed
                assert '`®pessoa`' in renamed
                inside=c.solicite('textDocument/completion',c.no_ponto(uri,fixed,'segunda linha',dentro=3))
                assert not inside
            print('PASSOU incremental, Unicode e recuperação de delimitador',ext)
    finally: c.feche()
