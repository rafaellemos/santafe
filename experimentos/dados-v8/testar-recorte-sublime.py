#!/usr/bin/env python3
"""Recortador e contrato do pacote; não é teste de pixels/host do Sublime."""
from pathlib import Path
import importlib.util
ROOT=Path(__file__).resolve().parents[2]
kit=ROOT/'dist/candidato-dados-v22/editores/SantafeDados'
spec=importlib.util.spec_from_file_location('recorte8',kit/'realce_embutido.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
count=0
for n in (1,2,3,9):
    eq='='*n; body='®variável Ⓡ{1+2} `` \\n ]'+'='*(n+1)+']\ncontinua'
    source='local x=['+eq+'['+body+']'+eq+']; local y=`Ⓡvariável`'
    literals,_=m.recorte(source)
    assert len(literals)==2
    raw,template=literals
    assert raw['longo'] and not template['longo']
    assert source[raw['conteudo']:raw['fechamento']]==body
    assert not any(p.get('buraco') for p in raw['partes'])
    assert len([p for p in template['partes'] if p.get('buraco')])==1
    count+=1
for source in ('local x=[[1],[2]]','--[[ [=[não é colar]=] ]]','--[==[ ®nome ]=] ]==]'):
    assert not m.recorte(source)[0]; count+=1
syntax=(kit/'Santafe-Dados.sublime-syntax').read_text()
assert "- match: '\\[(=+)\\['" in syntax and "- match: '\\]\\1\\]'" in syntax
assert "- match: '``'" not in syntax
print('SUBLIME_RECORTE_DELIMITADORES8_OK',count,'(UI nativa não ensaiada)')
