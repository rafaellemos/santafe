#!/usr/bin/env python3
"""Mantém os critérios21, separa 2.1 histórica de 3 padrão e migra a embalagem."""
from pathlib import Path
import shutil
import subprocess
import sys

repo = Path(__file__).resolve().parent.parent
dest = repo/'apoio25'
assert not dest.exists() and not (repo/'apoio21').exists()
for script in ('preparar-bateria.py', 'preparar-instalador.py'):
    subprocess.run([sys.executable, str(repo/'dados21'/script)], check=True)
shutil.copytree(repo/'apoio21', dest)

for p in dest.rglob('*'):
    if p.suffix not in ('.py', '.ps1') or 'base21' in p.parts or 'base' in p.parts:
        continue
    s = p.read_text(encoding='utf-8')
    for a, b in [('dados.21', 'dados.25'), ('dados21', 'dados25'),
                 ('3.0.21', '3.0.25'), ('3,0,21,0', '3,0,25,0'),
                 ('/santafé/1.0/', '/santafé/3.0/')]:
        s = s.replace(a, b)
    # A base continua sendo o MSI20 original. Só o candidato/falha mudam.
    s = s.replace("'3.0.22'", "'3.0.26'").replace('fixture-falha22', 'fixture-falha26')
    s = s.replace("'-DSANTAFE_DADOS_EXPERIMENTAL',", '')
    if p.name == 'testar-instalador.py':
        for a, b in [('para21', 'para25'), ('instalacao21', 'instalacao25'),
                     ('preservou21', 'preservou25'), ('desinstalar21', 'desinstalar25'),
                     ('remover21', 'remover25'), ('20-21', '20-25'),
                     ('para22', 'para26')]:
            s = s.replace(a, b)
    if p.name == 'testar-windows11.py':
        for a, b in [('para21', 'para25'), ('candidato21', 'candidato25'),
                     ('reparar21', 'reparar25'), ('remover21', 'remover25')]:
            s = s.replace(a, b)
    if p.name == 'portatil.py':
        s = s.replace('Demais bibliotecas C e editores Windows ainda não homologados.',
                      'Este pacote25 exige sua própria homologação; resultados visuais21 são históricos.')
    p.write_text(s, encoding='utf-8')

p = repo/'windows/testar21.py'
s = p.read_text(encoding='utf-8').replace("'candidato':'dados.21'", "'candidato':'dados.25'")
old = "for name,flags in [('estavel',''),('candidato','-DSANTAFE_DADOS_EXPERIMENTAL -DLUA_USE_APICHECK')]:\n            stage=work/name;shutil.copytree(root,stage)"
new = """for name,flags in [('estavel',''),('candidato','-DLUA_USE_APICHECK')]:
            source = root if name == 'candidato' else root.parent/'fonte-estavel'
            assert (source/'PREPARACAO-WINDOWS.json').is_file()
            stage=work/name;shutil.copytree(source,stage)"""
assert s.count(old) == 1
s = s.replace(old, new).replace("'-DSANTAFE_DADOS_EXPERIMENTAL',", '')
s = s.replace('from dll import test as test_dll', 'from dll25 import test as test_dll')
anchor = "        cand=work/'candidato';stable=work/'estavel';exe=cand/'src/santafe.exe';old=stable/'src/santafe.exe'"
assert s.count(anchor) == 1
s = s.replace(anchor, anchor+'''
        sf('contrato-estavel-separado','garanta(tipo({})=="tabela"); garanta(json.cod({})=="{}"); local t={x=nulo};garanta(próximo(t)==nulo)',old,stable)
        sf('contrato3-padrao','garanta(tipo([])=="lista");garanta(tabela.temChave({x=nulo},"x"));garanta(json.cod([nulo])=="[null]")',exe,cand)
        disabled=work/'recusa-desligar-iba.c';disabled.write_text('#include "lua.h"\\n',encoding='utf-8')
        run('sdk-recusa-desligar-iba',['gcc','-DSANTAFE_DADOS_V3=0','-I'+str(cand/'src'),'-c',disabled,'-o',work/'recusa.o'],cand,expected=None)
''')
(repo/'windows/testar25.py').write_text(s, encoding='utf-8')
s = (repo/'windows/dll.py').read_text(encoding='utf-8').replace("'-DSANTAFE_DADOS_EXPERIMENTAL',", '')
(repo/'windows/dll25.py').write_text(s, encoding='utf-8')
for p in [*dest.rglob('*.py'), repo/'windows/testar25.py', repo/'windows/dll25.py']:
    compile(p.read_text(encoding='utf-8'), str(p), 'exec')
print('BATERIA25_PREPARADA: base2.1 separada; SDK3 padrão; caminhos3.0; critérios MSI preservados')
