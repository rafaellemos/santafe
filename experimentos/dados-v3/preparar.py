#!/usr/bin/env python3
"""Gera uma árvore descartável; nunca reescreve a árvore de trabalho.

O lexer estável migra só delimitadores. A lista de alterações abaixo é uma
revisão explícita de operações, não uma heurística geral sobre nulo/tabela.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
STABLE = ROOT / 'dist/candidato-dados-v2-baseline/santafé-dados'
assert STABLE.is_file(), 'construa primeiro o controle estável dados-v2'
dest = Path(tempfile.mkdtemp(prefix='santafe-dados3-', dir='/tmp'))
roots = ('src/', 'bibs/', 'testes/', 'exemplos/', 'aplicativos/', 'ferramentas/')
files = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
files = [f for f in files if f.startswith(roots)]
files += ['ferramentas/sls/estrutura.fé', 'docs/CONTRATO-DADOS-ONFE.md',
          'extensões/vscode/api-publica.json']
files += [str(p.relative_to(ROOT)) for p in (ROOT/'experimentos').rglob('*')
          if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc']
report = {'origem': str(ROOT), 'destino': str(dest), 'lexico': [], 'semantico': []}
for name in sorted(set(files)):
    src, out = ROOT/name, dest/name
    assert src.is_file() and not src.is_symlink(), name
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, out)
    if unicodedata.normalize('NFC', src.suffix) == '.fé' and name.startswith(('bibs/', 'testes/', 'exemplos/', 'aplicativos/')):
        p = subprocess.run([str(STABLE), '-E', '-P', str(ROOT/'experimentos/dados-v1/migrar.fé'), str(src)],
                           capture_output=True, check=True)
        if p.stdout != src.read_bytes():
            out.write_bytes(p.stdout)
            report['lexico'].append({'arquivo': name, 'sha256_antes': hashlib.sha256(src.read_bytes()).hexdigest(),
                                    'sha256_depois': hashlib.sha256(p.stdout).hexdigest()})

def change(name, old, new, count=None):
    path = dest/name
    text = path.read_text()
    found = text.count(old)
    assert found and (count is None or found == count), (name, old, found, count)
    path.write_text(text.replace(old, new))
    report['semantico'].append({'arquivo': name, 'antes': old, 'depois': new, 'ocorrencias': found})

# Remoção real de entradas; variáveis locais e campos opcionais mantêm nulo.
deletions = {
    'pulso': [('estado.visitadas', 'valor'), ('este.fila', 'este.inícioDaFila')],
    'caminheiro': [('res._ap._conexões','conexão'), ('ap._conexões','conexaoHTTP')],
    'correio': [('servidor.conexões','sessão')],
    'correio/imap': [('servidor.conexões','sessão')],
    'turing': [('desafios','id'), ('bilhetes','tk'), ('bilhetes','bilhete')],
    'vigia': [('chaves','chave'), ('chaves','chaveMaisAntiga')],
    'nomes/autoridade': [('este.conexões','estado')],
    'nomes/acesso': [('origens','endereço')],
    'nomes/resolvedor': [('memrap','chave'), ('estadosAtivos','estado'),
                         ('pendentes','estado.id'), ('pendentes','id'), ('conexõesTCP','estado')],
    'correio/spf': [('contexto.visitados','domínio')],
}
for mod, entries in deletions.items():
    for tab, key in entries:
        change(f'bibs/bibf/{mod}.fé', f'{tab}[{key}] = nulo', f'tabela.apague({tab}, {key})')
for mod, obj, field in [
    ('nomes/zona','opçõesDNSSEC','chavePrivada'), ('nomes/dnssec','chave','privada'),
    ('correio/mariadb','personalizados','regraDaTriagem'), ('correio/mariadb','personalizados','decididaEm'),
    ('correio/mariadb','mensagem','__remetentes'), ('correio/mariadb','mensagem','__anexos'),
    ('correio/multibanco','limpa','bancoPostal'), ('correio/dkim','resultado','motivo'),
    ('rpdf','img','dados'), ('rpdf','img','máscaraSuave'), ('rpdf','máscara','máscaraSuave')]:
    change(f'bibs/bibf/{mod}.fé', f'{obj}.{field} = nulo', f'tabela.apague({obj}, "{field}")')
change('bibs/bibf/rpdf.fé', 'caracteres[#caracteres] = nulo', 'tabela.remova(caracteres)')

# Dados PULSO são registros na raiz; listas explícitas são preservadas dentro.
change('bibs/bibf/pulso.fé', 'se espécie ~= "tabela" então', 'se espécie ~= "tabela" e espécie ~= "lista" então', 1)
change('bibs/bibf/pulso.fé', 'local cópia = {}', 'local cópia = espécie == "lista" e [] ou {}', 1)
change('bibs/bibf/nomes.fé', 'se tipo(valor) ~= "tabela" então erro("TXT',
       'se tipo(valor) ~= "tabela" e tipo(valor) ~= "lista" então erro("TXT', 1)

# Fronteiras de sequências conhecidas pelo contrato postal. O adaptador recusa
# tabelas esparsas/mistas em vez de perder entradas silenciosamente.
shutil.copy2(ROOT/'experimentos/dados-v3/sequências.fé', dest/'bibs/bibf/dados_experimentais.fé')
for mod in ('correio', 'correio/mariadb'):
    path = dest/f'bibs/bibf/{mod}.fé'
    path.write_text('local dados = importe "dados_experimentais"\n'+path.read_text())
change('bibs/bibf/correio.fé', 'proteja(json.cod, destinatários)', 'proteja(dados.codifiqueLista, destinatários)', 1)
change('bibs/bibf/correio/mariadb.fé', 'local função listaJSON(valor)', 'local função listaJSON(valor, registro)', 1)
change('bibs/bibf/correio/mariadb.fé', 'proteja(json.cod, valor)',
       'proteja(registro e dados.codifiqueDestinatários ou dados.codifiqueLista, valor)', 1)
change('bibs/bibf/correio/mariadb.fé', 'listaJSON(dados.destinatários ou {})',
       'listaJSON(dados.destinatários ou {}, verdadeiro)', 1)
change('bibs/bibf/correio/mariadb.fé', 'tipo(decodificado) ~= "tabela"',
       'tipo(decodificado) ~= "tabela" e tipo(decodificado) ~= "lista"', 1)
for name in ('destinatáriosPendentes', 'falhasPermanentes', 'falhasPermanentes ou {}'):
    change('bibs/bibf/correio.fé', f'proteja(json.cod,\n            {name})',
           f'proteja(dados.codifiqueLista,\n            {name})')
for mod in ('correio', 'correio/imap'):
    change(f'bibs/bibf/{mod}.fé', 'rastro = {}', 'rastro = []', 1)
change('bibs/bibf/correio.fé', 'se tipo(valor) ~= "tabela" então\n        retorne nulo, nome .. " deve ser um endereço ou uma lista"',
       'se tipo(valor) ~= "tabela" e tipo(valor) ~= "lista" então\n        retorne nulo, nome .. " deve ser um endereço ou uma lista"', 1)
for mod, name in [('correio','destinatáriosPendentes'), ('correio/entrega','destinatários')]:
    change(f'bibs/bibf/{mod}.fé', f'se tipo({name}) ~= "tabela" ou',
           f'se (tipo({name}) ~= "tabela" e tipo({name}) ~= "lista") ou', 1)

# O banco falso também precisa cumprir DELETE; as verificações ficam intactas.
for tab, key in [('piscina.remetentesConfiáveis','parâmetros[2]'),
                 ('piscina.regrasDaTriagem','parâmetros[2] .. ":" .. parâmetros[3]')]:
    change('testes/bibc/teste_carteiro_repositorio.fé', f'{tab}[{key}] = nulo', f'tabela.apague({tab}, {key})', 1)
change('testes/bibf/teste_correio.fé', 'tipo(fechamento.dados.rastro) == "tabela"',
       'tipo(fechamento.dados.rastro) == "lista"', 1)
# Corpus de análise deve testar delimitadores novos; o migrador não altera
# programas representados dentro de colares curtos (isso exigiria adivinhação).
change('testes/bibf/teste_analise_sintatica.fé', '[=[não terminou', '``não terminou', 2)
change('testes/bibf/teste_analise_sintatica.fé', '[[<div>]]', '``<div>``', 1)
change('testes/integracao/sls/corpus.fé', 'local falhas={}', 'local falhas=[]', 1)
change('testes/integracao/sls/corpus.fé', 'A.analise(fonte,caminho)', 'A.analise(fonte,caminho,verdadeiro)', 1)
change('testes/integracao/sls/corpus.fé', 'erros=a.erros', 'erros=[tabela.desempacote(a.erros)]', 1)

# A identificação deste laboratório é explícita; os artefatos dados.2 não mudam.
change('src/lua.h', '#define SANTAFE_DADOS_VERSION "dados.2"', '#define SANTAFE_DADOS_VERSION "dados.3"', 1)
change('ferramentas/sls/sls.fé', '1.0.0-dados.2', '1.0.0-dados.3', 1)
(dest/'MIGRACAO.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
(dest/'.laboratorio-dados3').write_text('somente testes isolados\n')
print(dest)
