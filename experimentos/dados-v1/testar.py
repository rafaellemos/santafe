#!/usr/bin/env python3
"""Regressão cruzada: núcleo candidato, núcleo estável, migração e ONFÉ."""
import json
import os
import pathlib
import random
import subprocess
import sys
import tempfile
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
CAND=pathlib.Path(os.environ.get("SANTAFE_CANDIDATO",ROOT/"dist/candidato-dados-v1/santafé-dados"))
DEFAULT_STABLE=ROOT/"src/santafé"
if not DEFAULT_STABLE.exists():
    DEFAULT_STABLE=ROOT/"dist/candidato-dados-v1-baseline/santafé-dados"
STABLE=pathlib.Path(os.environ.get("SANTAFE_ESTAVEL",DEFAULT_STABLE))

def run(binary, *args, text=None, timeout=20):
    return subprocess.run([str(binary),"-E","-P",*map(str,args)],input=text,text=True,
                          capture_output=True,cwd=ROOT,timeout=timeout)

class Candidate(unittest.TestCase):
    def code(self, source):
        p=run(CAND,"-e",source)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        return p.stdout

    def test_modules(self):
        for name in ("testar.fé","testar-onfe.fé","testar-sls.fé","exemplo.fé"):
            with self.subTest(name=name):
                p=run(CAND,ROOT/"experimentos/dados-v1"/name)
                self.assertEqual(p.returncode,0,p.stdout+p.stderr)

    def test_null_paths(self):
        self.code('''local t={}; local vazio
defina(t,"a",vazio); garanta(tabela.temChave(t,"a")); garanta(igual(obter(t,"a"),nulo))
garanta(t[obter(t,"a")]==nulo); garanta(próximo(t,t.a)=="a")
local ok=proteja(função() t[t.a]=1 fim); garanta(não ok)
local n=0; para k em função() retorne t.a fim início n=n+1; garanta(n<2) fim
garanta(n==0)
local m=definaMetatabela({1,2},{__tamanho=nulo}); garanta(#m==2)
local mt={__índice=nulo}; local o=definaMetatabela({},mt)
garanta(o.x==nulo); mt.__índice=função() retorne 42 fim; garanta(o.x==42)
mt.__índice=nulo; garanta(o.x==nulo)
mostre("NULL_PATHS_OK")''')

    def test_dense_mutations_and_gc(self):
        self.code('''local l=[]; local r={}; local n=0
para i=1,3000 início
    local v=i; se i%3==0 então v=nulo fim
    se i%4==0 e n>0 então
        local pos=(i%n)+1
        tabela.remova(l,pos)
        para j=pos,n-1 início r[j]=r[j+1] fim
        tabela.apague(r,n); n=n-1
    senão n=n+1; l[n]=v; r[n]=v fim
    garanta(#l==n)
    se i%71==0 então coleteLixo("colete") fim
    para j=1,n início garanta(l[j]==r[j] e tabela.temChave(l,j)) fim
fim
local função f() retorne nulo,nulo fim
local v=[f()]; garanta(#v==2 e tabela.temChave(v,2))
local x=[]; para i=1,200 início x[i]={a=nulo} fim
coleteLixo("colete"); garanta(tabela.temChave(x[200],"a"))''')

    def test_bad_indices_atomic(self):
        for idx in ('0','-1','1.5','"1"','nulo','{}','mat.infinito','0/0','1000000000'):
            with self.subTest(idx=idx):
                self.code(f'local l=[1,2]; local ok=proteja(função() l[{idx}]=3 fim); garanta(não ok e #l==2 e l[2]==2)')
        self.code('local l=[1]; local ok=proteja(definaMetatabela,l,{}); garanta(não ok)')

    def test_json_exact_and_unique(self):
        self.code('''local x=9223372036854775807
garanta(json.cod(x)=="9223372036854775807")
garanta(json.decod(json.cod(x))==x)
garanta(json.decod("-9223372036854775808")==(-9223372036854775807-1))
local ok=proteja(json.decod,'{"a":null,"a":1}'); garanta(não ok)
garanta(json.cod(json.decod("[null,{},[],false]"))=="[null,{},[],false]")''')

    def test_onfe_limits_and_no_effects(self):
        self.code('''local O=executeArquivo("experimentos/dados-v1/onfé.fé")
local ok=proteja(O.decod,(' '):replique(4*1024*1024+1)); garanta(não ok)
_G.ONFE_EXECUTOU=falso
ok=proteja(O.decod,'{a=(função() ONFE_EXECUTOU=verdadeiro fim)()}')
garanta(não ok e ONFE_EXECUTOU==falso)
local a={x=1}; local t={a=a,b=a}; local volta=O.decod(O.cod(t)); garanta(volta.a.x==1 e volta.b.x==1)
local b=O.decod('{[falso]=nulo,[1]="a",["1"]="b"}')
garanta(tabela.temChave(b,falso) e b[1]~=b["1"])''')

    def test_json_onfe_roundtrips_seeded(self):
        rng=random.Random(20261023)
        def value(depth):
            leaves=[None,True,False,0,1,-7,2147483647,9223372036854775807,
                    1.2345678901234567,1.7976931348623157e308,2.2250738585072014e-308,
                    "José","","a\x00b",'"[]{}®Ⓡ']
            if depth<=0 or rng.randrange(3)==0:
                return rng.choice(leaves)
            if rng.randrange(2):
                return [value(depth-1) for _ in range(rng.randrange(6))]
            return {k:value(depth-1) for k in rng.sample(["a","1","01","tipo","entradas","nulo","índice"],rng.randrange(6))}
        values=[value(5) for _ in range(500)]
        source='local O=executeArquivo("experimentos/dados-v1/onfé.fé"); local texto=es.entradaPadrão:leia("*tudo"); mostre(json.cod(O.decod(O.cod(json.decod(texto)))))'
        p=run(CAND,"-e",source,text=json.dumps(values,ensure_ascii=False),timeout=30)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(json.loads(p.stdout),values)

    def test_migration_semantics(self):
        old='''--[[ comentário com [[ colchetes ]]
local a=[=[
linha ®nome \\n]=]
local b=[[1]]
local c=[[texto `` no meio]]
local d=``
local texto="[[texto]]"
local t={a=nulo}
mostre(a); mostre(b); mostre(c); mostre(d); mostre(texto)
'''
        with tempfile.TemporaryDirectory(prefix="santafe-migracao-") as tmp:
            before=pathlib.Path(tmp)/"antes.fé"
            after=pathlib.Path(tmp)/"depois.fé"
            before.write_text(old)
            migrated=run(STABLE,ROOT/"experimentos/dados-v1/migrar.fé",before)
            self.assertEqual(migrated.returncode,0,migrated.stderr)
            self.assertIn("REVISAR",migrated.stderr)
            self.assertEqual(before.read_text(),old)
            after.write_text(migrated.stdout)
            old_result=run(STABLE,before); new_result=run(CAND,after)
            self.assertEqual(old_result.returncode,0,old_result.stderr)
            self.assertEqual(new_result.returncode,0,new_result.stderr)
            self.assertEqual(old_result.stdout,new_result.stdout)
            self.assertIn('a=nulo',after.read_text())

    def test_bytecode_separation(self):
        with tempfile.TemporaryDirectory(prefix="santafe-bytecode-") as tmp:
            source=pathlib.Path(tmp)/"teste.fé"; out=pathlib.Path(tmp)/"teste.bin"
            source.write_text('local l=[nulo]; garanta(#l==1); mostre("bytecode candidato")')
            compiler=CAND.parent/"santafec-dados"
            p=subprocess.run([str(compiler),"-o",str(out),str(source)],capture_output=True,text=True,timeout=20)
            self.assertEqual(p.returncode,0,p.stderr)
            p=run(CAND,out); self.assertEqual(p.returncode,0,p.stderr)
            p=run(STABLE,out); self.assertNotEqual(p.returncode,0)

    def test_stable_unchanged(self):
        self.assertEqual(run(STABLE,"-e",'mostre(tipo({})); local t={a=nulo}; mostre(próximo(t))').stdout,"tabela\nnulo\n")
        for test in ("testes/bibf/teste_json.fé","testes/metatabelas.fé","testes/bibf/teste_gabarito_unicode.fé","testes/bibf/teste_sls_analisador.fé"):
            with self.subTest(test=test):
                p=run(STABLE,test)
                self.assertEqual(p.returncode,0,p.stderr)

if __name__=="__main__":
    unittest.main(verbosity=2)
