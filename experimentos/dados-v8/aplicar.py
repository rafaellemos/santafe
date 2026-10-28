#!/usr/bin/env python3
"""Receita de revisão léxica. Modifica apenas a árvore candidata marcada."""
from pathlib import Path
import html, json, re, shutil, subprocess, tempfile
ROOT=Path(__file__).resolve().parents[2]
assert (ROOT/'.laboratorio-dados8').is_file()
def change(name,old,new,count=1):
    p=ROOT/name; t=p.read_text(); assert t.count(old)==count,(name,old,t.count(old))
    p.write_text(t.replace(old,new))

p=ROOT/'src/llex.c'; t=p.read_text()
start=t.index('#ifdef SANTAFE_DADOS_EXPERIMENTAL',t.index('static int read_string'))
end=t.index('#endif',start)+len('#endif\n')
t=t[:start]+t[end:]
old='''#ifdef SANTAFE_DADOS_EXPERIMENTAL
        next(ls);
#else
        size_t sep = skip_sep(ls);
        if (sep >= 2) {'''
new='''        size_t sep = skip_sep(ls);
#ifdef SANTAFE_DADOS_EXPERIMENTAL
        /* Pelo menos um '=': [[1],[2]] continua sendo lista de listas. */
        if (sep >= 3) {
#else
        if (sep >= 2) {
#endif'''
assert old in t; t=t.replace(old,new)
t=t.replace('''#endif
        return '[';''','''        return '[';''',1)
p.write_text(t)

# O lexer antigo só é necessário na preparação. Testes novos geram seus dados
# com os delimitadores novos; os relatórios históricos não são reescritos.
def raw(v):
    level=1
    while True:
        end=']'+'='*level+']'
        if (v+end).find(end)==len(v):
            return '['+'='*level+'['+ ('\n' if v.startswith(('\n','\r')) else '')+v+end
        level+=1
def fixture(t):
    return re.sub(r'``(.*?)``',lambda m:raw(m[1]),t,flags=re.S)
for name in ('experimentos/dados-v1/testar-editores.js','experimentos/dados-v2/testar-editores.js',
             'experimentos/dados-v2/testar-sls.py','experimentos/dados-v3/testar-wasm.js',
             'experimentos/dados-v5/testar-instalacao.py','experimentos/dados-v5/testar-atualizacao.py',
             'experimentos/dados-v6/testar-recorte-sublime.py','experimentos/dados-v7/testar-persistencia.py'):
    p=ROOT/name; p.write_text(fixture(p.read_text()))
for name in ('experimentos/dados-v1/testar-onfe.fé','experimentos/dados-v1/testar-sls.fé','experimentos/dados-v4/testar-colares.fé'):
    p=ROOT/name; p.write_text(fixture(p.read_text()))
change('testes/integracao/testar_sls_semantica.py',
       "text=text.replace(literal,'``a\\n  b\\n c``'); literal='``a\\n  b\\n c``'",
       "text=text.replace(literal,'[=[a\\n  b\\n c]=]'); literal='[=[a\\n  b\\n c]=]'")
change('testes/integracao/sls/casos.py',
       "texto.replace(' [[', ' ``').replace(']] ..', '`` ..').replace('>]]', '>``').replace(';]]', ';``')",
       "texto.replace(' [[', ' [=[').replace(']] ..', ']=] ..').replace('>]]', '>]=]').replace(';]]', ';]=]')")
change('testes/integracao/sls/casos.py',".replace('[[', '``').replace(']]', '``')",
       ".replace('[[', '[=[').replace(']]', ']=]')",2)
# Fontes propositalmente inválidos nos ensaios de diagnósticos.
change('testes/bibf/teste_analise_sintatica.fé','``não terminou','[=[não terminou',2)
change('testes/bibf/teste_analise_sintatica.fé','``<div>``','[=[<div>]=]')

# Migrador da versão estável: preserva níveis com '=', converte só [[...]],
# sem executar o fonte e sem confundir comentários/listas dos candidatos.
p=ROOT/'experimentos/dados-v1/migrar.fé'; t=p.read_text()
start=t.index('    se t.tipo=="colar"')
end=t.index('    se novo então',start)
t=t[:start]+'''    se t.tipo=="colar" e t.texto:corte(1,2)=="[[" então
        local nivel=1
        enquanto verdadeiro início
            local iguais=("="):replique(nivel)
            local fecha="]"..iguais.."]"
            se (t.valor..fecha):procure(fecha,1,verdadeiro)==#t.valor+1 então
                local prefixo=t.valor:corte(1,1)=="\\n" e "\\n" ou ""
                novo="["..iguais.."["..prefixo..t.valor..fecha
                pare
            fim
            nivel=nivel+1
        fim
    fim
'''+t[end:]
p.write_text(t)

# Recortadores: comentário aceita zero '=', colar bruto exige um ou mais.
change('extensões/vscode/realce-embutido.js','const LONGO = /\\[(=*)\\[/y;',
       'const LONGO = /\\[(=*)\\[/y;\nconst BRUTO = /\\[(=+)\\[/y;')
change('extensões/vscode/realce-embutido.js','  function comentário() {',
       '  function bruto() { BRUTO.lastIndex = i; return BRUTO.exec(fonte); }\n  function comentário() {')
change('extensões/vscode/realce-embutido.js','DIALETO_DADOS ? (fonte.startsWith("``", i) ? ["``"] : null) : longo()',
       'DIALETO_DADOS ? bruto() : longo()')
change('extensões/vscode/realce-embutido.js','(DIALETO_DADOS ? "``" : "]" + abre[1] + "]")', '"]" + abre[1] + "]"')
change('extensões/vscode/realce-embutido.js','(!DIALETO_DADOS && longo())','(DIALETO_DADOS ? bruto() : longo())')
change('extensões/sublime/realce_embutido.py','LONGO = re.compile(r"\\[(=*)\\[")',
       'LONGO = re.compile(r"\\[(=*)\\[")\nBRUTO = re.compile(r"\\[(=+)\\[")')
change('extensões/sublime/realce_embutido.py','(fonte.startswith("``", i) if DADOS_EXPERIMENTAIS else LONGO.match(fonte, i))',
       '(BRUTO if DADOS_EXPERIMENTAIS else LONGO).match(fonte, i)')
change('extensões/sublime/realce_embutido.py','("``" if DADOS_EXPERIMENTAIS else "]" + abre[1] + "]")','("]" + abre[1] + "]")')
change('extensões/sublime/realce_embutido.py','(i + 2 if DADOS_EXPERIMENTAIS else abre.end())','abre.end()')
change('extensões/sublime/realce_embutido.py','(not DADOS_EXPERIMENTAIS and LONGO.match(fonte, i))',
       '(BRUTO if DADOS_EXPERIMENTAIS else LONGO).match(fonte, i)')
change('experimentos/dados-v1/editores.py','"begin": "``", "end": "``"',r'"begin": r"\[(=+)\[", "end": r"\]\1\]"')
change('experimentos/dados-v1/editores.py',"    - match: '``'\n      push:\n        - meta_scope: string.quoted.other.raw.santafe\n        - match: '``'",
       "    - match: '\\[(=+)\\['\n      push:\n        - meta_scope: string.quoted.other.raw.santafe\n        - match: '\\]\\1\\]'")
# Nome/versionamento do kit isolado, sem tocar na extensão estável instalada.
p=ROOT/'experimentos/dados-v2/editores.py'; t=p.read_text()
t=t.replace('candidato-dados-v2/editores','candidato-dados-v8/editores').replace('dados.2','dados.8').replace('0.0.2','0.0.8').replace('EDITORES_DADOS_2_OK','EDITORES_DADOS_8_OK')
p.write_text(t)
change('experimentos/dados-v2/testar-editores.js','candidato-dados-v2/editores','candidato-dados-v8/editores')

for name in ('src/lua.h','ferramentas/sls/sls.fé','Makefile','instalar.sh',
             'experimentos/dados-v3/testar-wasm.js','experimentos/dados-v5/testar-instalacao.py',
             'experimentos/dados-v6/testar-operacao.py','experimentos/dados-v6/operacao.py'):
    p=ROOT/name; p.write_text(p.read_text().replace('dados.7','dados.8'))

# Exemplos reais do manual, migrados pelo lexer dados.7 e reescapados como HTML.
p=ROOT/'docs/manual.html'; t=p.read_text()
def migrate(m):
    code=html.unescape(m[2])
    if '``' not in code: return m[0]
    with tempfile.TemporaryDirectory(prefix='manual8-') as tmp:
        f=Path(tmp)/'exemplo.fé'; f.write_text(code)
        proc=subprocess.run([str(ROOT/'nucleo-dados7'),'-E','-P',str(ROOT/'experimentos/dados-v8/migrar-candidato.fé'),str(f)],capture_output=True,text=True,check=True)
        return m[1]+html.escape(json.loads(proc.stdout)['texto'],quote=False)+m[3]
t=re.sub(r'(<code\b[^>]*id="[^"]+"[^>]*>)(.*?)(</code>)',migrate,t,flags=re.S)
t=t.replace('Dois acentos graves delimitam colares brutos; um delimita gabaritos ® e Ⓡ.',
    'Colares brutos usam [=[...]=], [==[...]==] e níveis maiores com a mesma quantidade de =. Um acento grave delimita gabaritos ® e Ⓡ. A primeira quebra imediatamente após a abertura do colar bruto é descartada, como na sintaxe antiga; CRLF e CR são normalizados para LF. Dois acentos graves juntos voltam a representar apenas um gabarito vazio, não um delimitador bruto.')
t=t.replace('--[[html]] ``','--[[html]] [=[').replace('--[[javascript]] ``','--[[javascript]] [=[')
t=t.replace('dados.7','dados.8').replace('prism-dados6.js','prism-dados8.js')
p.write_text(t)
prism=(ROOT/'experimentos/dados-v6/prism-dados6.js').read_text().replace('/``[\\s\\S]*?``/u',r'/\[(=+)\[[\s\S]*?\]\1\]/u')
(ROOT/'experimentos/dados-v8/prism-dados8.js').write_text(prism)
visual=(ROOT/'experimentos/dados-v6/visual.py').read_text().replace('dados.6','dados.8').replace('prism-dados6','prism-dados8').replace('dados-v6/prism','dados-v8/prism')
(ROOT/'experimentos/dados-v8/visual.py').write_text(visual)
for p in (ROOT/'docs').rglob('prism-dados6.js'):
    (p.parent/'prism-dados8.js').write_text(prism)
print('DADOS8_APLICADO: núcleo, migradores, SLS/ONFÉ, kits de editores e manual')
change('experimentos/dados-v3/testar-wasm.js','const deadline=setTimeout',
       'cases.push(fs.readFileSync(path.join(root,"experimentos/dados-v8/wasm.fé"),"utf8"));\nconst deadline=setTimeout')
