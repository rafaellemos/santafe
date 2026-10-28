#!/usr/bin/env python3
"""Migra a cópia do manual; documentação estável do repositório não é alterada."""
import html, json, re, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
assert (ROOT/'.laboratorio-dados6').exists()
p=ROOT/'docs/manual.html'; text=p.read_text(); changes=[]
def replace(old,new):
    global text
    assert old in text,old
    changes.append(old); text=text.replace(old,new)
replace('<title> Santafé | Manual </title>','<title>Santafé | Manual candidato dados.6</title>')
replace('</head>', '''<style>
@media (max-width:600px) {
  #ManualConteúdo table.sf-tabela-fn { min-width:0; width:100%; table-layout:fixed; }
  #ManualConteúdo .sf-tabela-fn th,
  #ManualConteúdo .sf-tabela-fn td,
  #ManualConteúdo .sf-tabela-fn td:first-child,
  #ManualConteúdo .sf-tabela-fn code { white-space:normal; overflow-wrap:anywhere; }
}
</style></head>''')
replace('/estático/wasm/2.0.3/','/estático/wasm/candidato-dados.6/')
replace('<script src="/estático/js/prism-santafé.js"></script>',
        '<script src="/estático/js/prism-santafé.js"></script>\n    <script src="/estático/js/prism-dados6.js"></script>')
replace('Ausência de valor.</td>','Valor nulo armazenável; falso em decisões. Ausência de chave é consultada separadamente.</td>')
replace('<h3 id="guia-tabelas">Tabelas</h3>','<h3 id="guia-tabelas">Tabelas e listas</h3>')
replace('A tabela é a estrutura central de Santafé: representa listas, registros, mapas e objetos. O primeiro índice de uma lista é <code>1</code>.',
        'Tabelas <code>{}</code> representam registros, mapas e objetos, incluindo chaves numéricas esparsas. Listas <code>[]</code> são sequências densas de tipo próprio; o primeiro índice é <code>1</code>.')
replace('linguagens = { "Santafé", "C" }','linguagens = [ "Santafé", "C" ]')
replace('Iterador para percorrer a parte de lista (índices 1..n) de uma tabela.',
        'Percorre todas as posições de uma lista, inclusive nulas. Em tabelas, percorre a sequência até o primeiro valor nulo; use pares para todas as chaves.')
replace('local página = --[[html]] [[','local página = --[[html]] ``')
replace('local código = --[[javascript]] [[','local código = --[[javascript]] ``')
replace('Nos pacotes de editor VS Code 1.1.0 e Sublime 1.1.0,',
        'Nos kits experimentais dos editores VS Code e Sublime, separados das extensões estáveis,')
replace('<code>--[[js]]</code> não é uma anotação reconhecida nesta versão.',
        '<code>--[[js]]</code> também é reconhecida como JavaScript. A inspeção visual nativa do candidato atual ainda é um gate separado dos testes de gramática.')
replace('<code>tamanho</code> aceita colares e tabelas;',
        '<code>tamanho</code> aceita colares, tabelas e listas;')
replace('sua medida estrutural nativa para colares e tabelas.',
        'sua medida estrutural nativa para colares, tabelas e listas.')
replace('Cada linha vem como uma tabela sequencial de colares, na ordem das colunas da consulta. Um <code>NULL</code> do SQL chega como <code>nulo</code>; o fim das linhas também é indicado por <code>nulo</code> retornado no lugar da tabela.',
        'Cada linha vem como uma lista nativa, na ordem das colunas da consulta. Colunas não nulas são colares; <code>NULL</code> do SQL ocupa uma posição com <code>nulo</code>, inclusive no meio ou no fim. O fim das linhas é indicado por <code>nulo</code> retornado no lugar da lista.')
replace('<td>tabela sequencial iniciada em 1</td>','<td>lista nativa iniciada em 1, inclusive vazia</td>')
replace('<td>número flutuante</td>','<td>inteiro quando representável sem perda; flutuante nos demais casos</td>')
replace('<code>json.valorNulo</code>, um <code>dadoOpaco</code> especial','<code>nulo</code> armazenável')
old='<code>nulo</code> numa tabela Santafé remove aquela chave; por isso <code>json.valorNulo</code> preserva explicitamente um valor JSON <code>null</code>. Uma tabela vazia codifica como <code>{}</code>; quando o protocolo exigir explicitamente a matriz vazia <code>[]</code>, use <code>json.matrizVazia</code>.'
replace(old,'<code>nulo</code> conserva a chave. <code>tabela.temChave</code> distingue presença; <code>tabela.apague</code> remove explicitamente. <code>[]</code> vira array JSON e <code>{}</code> vira objeto, sem adivinhar pelo primeiro índice. <code>json.valorNulo</code> e <code>json.matrizVazia</code> são formas legadas; prefira nulo e [].')
replace('apelido = json.valorNulo','apelido = nulo')
replace('json.cod({1, 2, 3})','json.cod([1, 2, 3])')
replace('j2.cod({1, 2})','j2.cod([1, 2])')
replace("mostre(json.decod('{\"a\":1,\"b\":[1,2,3]}').a)\n\n-- saída: 1.0", "mostre(json.decod('{\"a\":1,\"b\":[1,2,3]}').a)\n\n-- saída: 1")
replace('-- saída: dadoOpaco','-- saída: nulo')
replace('As chaves de um objeto precisam ser colares. Tabelas sequenciais viram matrizes; tabelas com chaves em colar viram objetos. Como uma tabela vazia não revela sua intenção, ela vira <code>{}</code>; use <code>json.matrizVazia</code> para emitir <code>[]</code>, por exemplo em campos de listas vazias de protocolos. Referências circulares e estruturas acima da profundidade configurada provocam erro.',
        'Listas viram arrays e tabelas viram objetos com chaves textuais. Tabelas com chaves numéricas ou lógicas são recusadas pelo JSON comum; ONFÉ pode preservá-las. Chaves duplicadas na leitura, ciclos e profundidade excedida provocam erro. Não converta automaticamente a chave textual "1" em número.')
replace('Números JSON viram sempre número de ponto flutuante Santafé (por isso <code>1.0</code>, não <code>1</code>), mesmo quando o texto original não tinha ponto decimal.',
        'Inteiros JSON na faixa de 64 bits mantêm a representação inteira. Valores decimais usam ponto flutuante. Outros consumidores, como JavaScript, podem ter uma faixa inteira exata menor.')
# A opção antiga não permite matrizes esparsas no contrato estrito do candidato.
replace('Configura como <code>json.cod</code> lida com listas esparsas (com buracos nos índices).',
        'Opção legada: não permite buracos nas listas nativas nem chaves numéricas em objetos JSON do candidato.')
replace('Chamado sem argumentos, só devolve a configuração atual (o padrão: não converte, razão 2, seguro 10). <code>converte</code> liga/desliga a conversão pra objeto (em vez de dar erro); <code>razão</code> e <code>seguro</code> controlam o quão esparsa uma lista pode ser antes de contar como "esparsa demais".',
        'A configuração legada pode ser consultada, mas não relaxa o contrato estrito: para arrays use [], para objetos use chaves textuais em {}. Tabelas esparsas continuam úteis em Santafé e ONFÉ, não em JSON comum.')
block=(ROOT/'experimentos/dados-v6/manual-dados.html').read_text()
block=re.sub(r'<div class="sf-code">(<button.*?</button><button.*?</button>)',
    r'<div class="sf-code" style="border-radius:14px;overflow:hidden;border:1px solid #cfd8dc;margin:16px 0">'
    r'<div class="sf-codebar" style="display:flex;align-items:center;gap:8px;padding:8px 12px;background:#edf5f3">\1</div>',block)
block=block.replace('class="sf-run"','class="sf-run btn-flat teal-text"').replace('class="sf-copy"','class="sf-copy btn-flat teal-text"')
block=block.replace('<pre class="language-santafé">','<pre class="language-santafé" style="margin:0;min-height:240px">')
replace('<h3 id="guia-tipos">Tipos e valores</h3>',block+'\n<h3 id="guia-tipos">Tipos e valores</h3>')
replace('<tr><td><code>lógico</code></td>', '<tr><td><code>lista</code></td><td><code>[1,nulo,3]</code>: sequência densa com comprimento próprio.</td></tr>\n<tr><td><code>lógico</code></td>')
# Migração léxica com o núcleo estável, jamais executando os exemplos.
binary=Path(sys.argv[1]).resolve()
count=0
def migrate(m):
    global count
    code=html.unescape(m[2])
    # Os novos exemplos já possuem sintaxe candidata; não passam pelo lexer antigo.
    if 'code-dados6-' in m[1]: return m[0]
    with tempfile.TemporaryDirectory(prefix='manual6-') as d:
        f=Path(d)/'exemplo.fé'; f.write_text(code)
        r=subprocess.run([str(binary),'-E','-P',str(ROOT/'experimentos/dados-v1/migrar.fé'),str(f)],capture_output=True,text=True)
        assert r.returncode==0,r.stderr
        if r.stdout!=code: count+=1
        return m[1]+html.escape(r.stdout,quote=False)+m[3]
text=re.sub(r'(<code\b[^>]*id="[^"]+"[^>]*>)(.*?)(</code>)',migrate,text,flags=re.S)
p.write_text(text)
(ROOT/'docs/MIGRACAO-MANUAL.json').write_text(json.dumps({'trechos_substituidos':changes,'exemplos_migrados_lexicamente':count},ensure_ascii=False,indent=2)+'\n')
print('Manual candidato preparado:',len(changes),'revisões;',count,'migrações léxicas')
