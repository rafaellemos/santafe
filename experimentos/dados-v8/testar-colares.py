#!/usr/bin/env python3
"""Contrato léxico/ONFÉ e migração: nunca executa o arquivo a migrar."""
from pathlib import Path
import json, os, random, subprocess, tempfile, unittest
ROOT=Path(__file__).resolve().parents[2]
CAND=ROOT/'src/santafé'
STABLE=Path(os.environ.get('SANTAFE_ESTAVEL',ROOT/'nucleo-estavel'))
OLD=Path(os.environ.get('SANTAFE_DADOS7',ROOT/'nucleo-dados7'))
BOOT='local O=executeArquivo("bibs/bibf/onfé.fé"); '
def run(binary,code):
    return subprocess.run([str(binary),'-E','-P','-e','\n'+code],cwd=ROOT,capture_output=True,text=True,timeout=15)
def literal(v,level=1):
    while True:
        end=']'+'='*level+']'
        if (v+end).find(end)==len(v):
            return '['+'='*level+'['+ ('\n' if v.startswith(('\n','\r')) else '')+v+end
        level+=1
def fequote(v):
    # JSON difere em escapes Unicode: preservar Unicode e usar escape decimal
    # para controles que JSON codificaria como \u00XX.
    return json.dumps(v,ensure_ascii=False).replace('\\u0000','\\000')
class Colares(unittest.TestCase):
    def ok(self,code):
        p=run(CAND,BOOT+code); self.assertEqual(p.returncode,0,p.stderr); return p.stdout
    def bad(self,code):
        p=run(CAND,code); self.assertNotEqual(p.returncode,0,p.stdout)
    def test_niveis_e_conteudo_literal(self):
        for n in (1,2,3,8,127):
            value='José e José 🟢 ®nome Ⓡ{erro()} \\n \\" `` ` [[ ]]'
            self.assertEqual(json.loads(self.ok('mostre(json.cod('+literal(value,n)+'))')),value)
    def test_fechamento_exato_nao_aninhado(self):
        for value in (']=]','a]==]b','[=[x]=]',']=','x]==',']===','\ntexto','\n\n'):
            self.assertEqual(json.loads(self.ok('mostre(json.cod('+literal(value)+'))')),value)
        self.assertEqual(self.ok('mostre([==[a]=]b]==])'),'a]=]b\n')
    def test_quebras_compativeis_com_estavel(self):
        for line in ('\n','\r','\r\n','\n\r'):
            for head in ('',line,line+line):
                source='mostre(json.cod([=['+head+'a'+line+'b]=]))'
                current=run(CAND,source); stable=run(STABLE,source)
                self.assertEqual(current.returncode,0,current.stderr)
                self.assertEqual(stable.returncode,0,stable.stderr)
                self.assertEqual(current.stdout,stable.stdout)
    def test_listas_indexacao_e_tabelas(self):
        self.ok('local l=[[1,nulo],[2]]; garanta(tipo(l)=="lista" e #l[1]==2); local t={["chave"]=9}; garanta(t[ [=[chave]=] ]==9); garanta(tipo({})=="tabela")')
    def test_bruto_vazio_e_gabarito_vazio(self):
        self.ok('garanta([=[]=]==""); garanta([==[]==]==""); garanta(``=="")')
        self.bad('local x=``texto``')
        # A semântica histórica de gabaritos vazios consecutivos é preservada;
        # o relevante é que o lexer não classifique isso como colar bruto.
        self.ok('local ts=depure.lexemas("````"); para _,t em ipares(ts) início garanta(t.tipo~="colar") fim')
    def test_gabaritos_unicode_e_funcoes_preservados(self):
        self.ok('local variável="José"; local variável="Ana"; garanta(`®variável Ⓡvariável`=="José Ana"); local f=função(x) retorne x*2 fim; garanta(f(5)==10)')
        self.bad('local f=(x)=>x*2')
    def test_comentarios_todos_niveis(self):
        self.ok('--[[ [=[ignorado]=] ]]\n--[==[ `` [nulo] ]=] ]==]\ngaranta([=[--[[literal]]]=]=="--[[literal]]")')
    def test_erro_na_abertura_e_fechamento(self):
        for value in ('[=x','[=[aberto','[==[errado]=]','[==[errado]===]','[=>texto<=]'):
            self.bad('local x='+value)
    def test_lexemas_posicoes_e_tipo(self):
        self.ok('local fonte="local ação=".."[==[®nome\\n]=]``]==]".."; local x=[[1]]"; local ts,f=depure.lexemas(fonte); garanta(não f); local n=0; para _,t em ipares(ts) início se t.tipo=="colar" então n=n+1; garanta(t.texto==fonte:corte(t["início"]+1,t["fim"])); garanta(t.valor=="®nome\\n]=]``") fim fim; garanta(n==1)')
    def test_onfe_dados_sem_execucao(self):
        self.ok('local v=O.decod("{texto=".."[==[Ⓡ{erro()}\\n``]=]]==]"..",itens=[nulo,{}]}"); garanta(v.texto=="Ⓡ{erro()}\\n``]=]"); garanta(#v.itens==2); garanta(O.deJSON(O.paraJSON(v)).texto==v.texto)')
        for value in ('`®nome`','``','``texto``','[[texto]]','função() fim'):
            self.ok('local ok=proteja(O.decod,'+fequote(value)+'); garanta(não ok)')
    def test_onfe_diagnostico_recuperacao(self):
        self.ok('local ok,f=O.analise("{x=[=[sem fim}"); garanta(não ok e f); garanta(O.analise("{x=[=[José]=]}"))')
    def test_corpus_aleatorio_comparado_com_estavel(self):
        rng=random.Random(20261023)
        for _ in range(100):
            v=''.join(rng.choice(['a','José','®','Ⓡ','[',']','=','`','\\n','\n','\r','>']) for _ in range(rng.randrange(1,80)))
            code='mostre(json.cod('+literal(v)+'))'
            a=run(STABLE,code); b=run(CAND,code)
            self.assertEqual(a.returncode,0,a.stderr); self.assertEqual(b.returncode,0,b.stderr)
            self.assertEqual(a.stdout,b.stdout)
    def test_migracao_estavel_sem_alterar_comentarios(self):
        source='--[[ [[não tocar]]\nlocal a=[[\nlinha ®nome \\n]]; local b=[==[\n]=]``]==]; local c="[[literal]]"; local d=``; mostre(a,b,c,d)'
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'antes.fé'; p.write_text(source)
            r=subprocess.run([str(STABLE),'-E','-P',str(ROOT/'experimentos/dados-v1/migrar.fé'),str(p)],cwd=ROOT,text=True,capture_output=True,timeout=15)
            self.assertEqual(r.returncode,0,r.stderr); self.assertEqual(p.read_text(),source)
            self.assertIn('--[[ [[não tocar]]',r.stdout); self.assertIn('[==[\n]=]``]==]',r.stdout)
            self.assertEqual(run(STABLE,source).stdout,run(CAND,r.stdout).stdout)
            result=run(CAND,r.stdout)
            self.assertEqual(result.returncode,0,result.stderr+'\n'+r.stdout)
    def test_migracao_dados7_preserva_quebra_inicial(self):
        for value in ('\na','\n\na','x]=','x]==','®literal\\n',''):
            source='local x=``'+value+'``; mostre(json.cod(x))'
            with tempfile.TemporaryDirectory() as d:
                p=Path(d)/'antes.fé'; p.write_text(source)
                r=subprocess.run([str(OLD),'-E','-P',str(ROOT/'experimentos/dados-v8/migrar-candidato.fé'),str(p)],cwd=ROOT,text=True,capture_output=True,timeout=15)
                self.assertEqual(r.returncode,0,r.stderr); migrated=json.loads(r.stdout)
                self.assertEqual(migrated['alterações'],1); self.assertEqual(p.read_text(),source)
                a=run(OLD,source); b=run(CAND,migrated['texto'])
                self.assertEqual(a.returncode,0,a.stderr); self.assertEqual(b.returncode,0,b.stderr)
                self.assertEqual(a.stdout,b.stdout)
if __name__=='__main__': unittest.main(verbosity=2)
