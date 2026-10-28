#!/usr/bin/env python3
"""Regressões das fronteiras lista/nulo do gerenciador, só fixtures locais."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'testes/integracao'))
from testar_pacotes import sf, lit

class Formatos(unittest.TestCase):
    def test_vazios_e_nulos(self):
        sf('garanta(F.canônico([])=="[]"); garanta(F.canônico({})=="{}"); '
           'garanta(F.canônico([nulo,{},[],falso])=="[null,{},[],false]"); '
           'garanta(F.canônico({a=nulo})==\'{"a":null}\'); '
           'local t={a=nulo}; tabela.apague(t,"a"); garanta(F.canônico(t)=="{}")')

    def test_canonico_aninhado(self):
        sf('garanta(F.canônico([{z=1,a=2},{b=nulo,a=[]}])=='
           '\'[{"a":2,"z":1},{"a":[],"b":null}]\'); '
           'garanta(F.canônico({["1"]="um"})==\'{"1":"um"}\')')

    def test_chaves_nao_sao_convertidas(self):
        for value in ('{1,2}', '{[1]="a",["1"]="b"}', '{[falso]=1}', '{[3]=1}'):
            with self.subTest(value=value):
                sf(f'F.canônico({value})',success=False)

    def test_lista_exige_tipo_explicito(self):
        for value in ('{}','{1,2}','"abc"','nulo'):
            sf(f'F.lista({value},10,"teste")',success=False)
        sf('garanta(F.lista([nulo,nulo],10,"teste")==2)')

    def test_limites_e_ciclos(self):
        sf('local x=[]; para i=1,66 início x=[x] fim; F.canônico(x)',success=False)
        sf('local x=[]; x[1]=x; F.canônico(x)',success=False)
        sf('local x={}; x.x=x; F.canônico(x)',success=False)
        sf('local x={a=nulo}; garanta(F.canônico([x,x])==\'[{"a":null},{"a":null}]\')')

    def test_metatabela_nao_executa(self):
        sf('local executou=falso; local t=definaMetatabela({},'
           '{__pares=função() executou=verdadeiro; erro("executado") fim}); '
           'local ok=proteja(F.canônico,t); garanta(não ok e não executou)')

    def test_json_recusa_duplicadas_e_raiz_lista(self):
        sf('F.json(\'{"a":null,"a":1}\')',success=False)
        sf('F.json("[]")',success=False)
        sf('garanta(tabela.temChave(F.json(\'{"a":null}\'),"a"))')

    def test_nativos_abi_e_listagem(self):
        with tempfile.TemporaryDirectory(prefix='dados4-nativo-') as tmp:
            sf(f'garanta(N.plataforma().abiDados); local r=garanta(N.raiz({lit(tmp)})); '
               'local l=garanta(r:liste()); garanta(tipo(l)=="lista" e json.cod(l)=="[]"); '
               'local ok=proteja(função() r:execute(["/usr/bin/printf",nulo],1) fim); '
               'garanta(não ok); r:feche()')

    def test_resolucao_recuo_preserva_selecao(self):
        sf('local R=importe "pacotes.resolvedor"; '
           'local c={a={["2.0.0"]={dependencias={b="2.0.0"}},["1.0.0"]={dependencias={b="1.0.0"}}},'
           'b={["2.0.0"]={dependencias={a="2.0.0"}},["1.0.0"]={}}}; '
           'local r=garanta(R.resolva(c,{a="*"})); '
           'garanta(r.pacotes.a.versao=="1.0.0" e r.pacotes.b.versao=="1.0.0"); '
           'garanta(#r.ordem==2 e r.ordem[1]=="b")')

if __name__=='__main__': unittest.main(verbosity=2)
