#!/usr/bin/env python3
"""Regressão pura do recortador do KIT experimental; não simula a UI nativa."""
import hashlib, importlib.util, json, sys, time
from pathlib import Path
kit=Path(sys.argv[1]).resolve()
p=kit/'SantafeDados/realce_embutido.py'
spec=importlib.util.spec_from_file_location('recorte_dados',p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
assert m.DADOS_EXPERIMENTAIS
total=0
for nome in ('variável','variável','índice','ação','𐐀nome'):
    for marca in ('®','Ⓡ'):
        fonte='local a=`🟢 '+marca+nome+'!`'
        partes=[p for l in m.recorte(fonte)[0] for p in l['partes'] if p.get('buraco')]
        assert [fonte[p['inicio']:p['fim']] for p in partes]==[marca+nome]
        total+=1
for fonte in ('local x=[=[®variável Ⓡ{1+2} \\n]=]', 'local x=[[1,nulo],[]]', '--[[ ®variável ]]'):
    assert not any(p.get('buraco') for l in m.recorte(fonte)[0] for p in l['partes'])
    total+=1
for fonte,final in (
    ('local x=--[[html]] [=[<a title="prefixo-]=] .. nome .. [=[-final">Olá</a>]=]','-final">Olá</a>'),
    ('local x=--[[js]] [=[/* comentário ]=] .. nome .. [=[ retomado */ const x=1;]=]',' retomado */ const x=1;'),
    ('local x=[=[<strong>automático</strong>]=]','automático</strong>'),
):
    docs=m.documentos_embutidos(fonte)
    assert len(docs)==1 and docs[0]['texto'].endswith(final),docs
    total+=1
fonte='local a = [=[<b title="]=] '+ '.. nome .. [=[x]=] '*3000+'.. [=[fim">Oi</b>]=]'
start=time.monotonic(); docs=m.documentos_embutidos(fonte)
assert len(docs)==1 and docs[0]['texto'].endswith('fim">Oi</b>')
elapsed=time.monotonic()-start
assert elapsed<5
total+=1
print(json.dumps({'resultado':'PASSOU','casos':total,'fragmentos':3000,
                 'segundos_recorte_grande':round(elapsed,4),
                 'arquivo':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
                 'limite':'recortador real; não é aprovação visual do Sublime'},ensure_ascii=False,indent=2))
