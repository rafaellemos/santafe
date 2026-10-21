#!/usr/bin/env python3
"""Gera realce sintático da mesma API pública usada nas conclusões.

Não resolve tipos em execução: chamadas por aliases recebem o escopo de chamada,
não uma alegação de que a função pertence à biblioteca original.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'ferramentas'))
from catalogo_editores import catalogue

ID = r'[\p{L}_][\p{L}\p{M}\p{N}_]*'
BEFORE = r'(?<![\p{L}\p{M}\p{N}_.:])'
AFTER = r'(?![\p{L}\p{M}\p{N}_])'
CONSTANTES = set('_G _VERSÃO _AMBIENTE mat.pi mat.infinito mat.máximoInteiro mat.mínimoInteiro utf8.padrãoCaractere nomes.CLASSES nomes.CÓDIGOS nomes.TIPOS json.valorNulo json.matrizVazia json._NOME json._VERSÃO'.split())


def alternativas(nomes):
    return '(?:' + '|'.join(re.escape(n) for n in sorted(nomes, key=lambda s: (-len(s), s))) + ')'


def regras_api(itens):
    globais = {i['rótulo'] for i in itens if not re.search('[.:]', i['rótulo'])} - CONSTANTES
    globais.add('importe')
    regras = [{'match': BEFORE + alternativas(globais) + AFTER, 'name': 'support.function.builtin.santafe'},
              {'match': BEFORE + alternativas(CONSTANTES) + AFTER, 'name': 'support.constant.santafe'}]
    grupos = {}
    for item in itens:
        nome = item['rótulo']
        if nome in CONSTANTES or not re.search('[.:]', nome):
            continue
        prefixo, separador, membro = re.match(r'(.+)([.:])([^.:]+)$', nome).groups()
        grupos.setdefault((prefixo, separador), []).append(membro)
    for (prefixo, separador), membros in sorted(grupos.items(), key=lambda p: -len(p[0][0])):
        padrao = BEFORE + '(' + re.escape(prefixo).replace(r'\.', r'\s*\.\s*') + r')\s*(' + re.escape(separador) + r')\s*(' + alternativas(membros) + ')' + AFTER
        escopo = ('variable.function.method.santafe' if separador == ':' else
                  'variable.other.member.santafe' if prefixo == 'req' else 'support.function.santafe')
        regras.append({'match': padrao, 'captures': {'1': {'name': 'support.namespace.santafe'},
                        '2': {'name': 'punctuation.accessor.santafe'}, '3': {'name': escopo}}})
    # Nomes de biblioteca são espaços de nomes, não palavras reservadas.
    # Chamadas do usuário/aliases também têm realce, sem executar importe.
    regras += [
        {'match': r'(:)\s*(' + ID + r')(?=\s*\()', 'captures': {
            '1': {'name': 'punctuation.accessor.santafe'}, '2': {'name': 'variable.function.method.santafe'}}},
        {'match': r'(?<![\p{L}\p{M}\p{N}_])' + ID + r'(?=\s*[.:])', 'name': 'variable.namespace.santafe'},
        {'match': r'(?<![\p{L}\p{M}\p{N}_])' + ID + r'(?=\s*\()', 'name': 'entity.name.function.call.santafe'},
    ]
    return regras


def yaml_regras(regras):
    linhas = []
    for r in regras:
        linhas.append("    - match: '" + r['match'].replace("'", "''") + "'")
        if 'name' in r:
            linhas.append('      scope: ' + r['name'])
        else:
            linhas.append('      captures:')
            linhas += ['        ' + n + ': ' + v['name'] for n, v in r['captures'].items()]
    return '\n'.join(linhas)


def principal():
    itens = catalogue()
    for pasta in ('vscode', 'sublime'):
        (ROOT / pasta / 'api-publica.json').write_text(json.dumps({'versão': 1, 'itens': itens}, ensure_ascii=False, indent=2) + '\n')
    (ROOT.parent / 'ferramentas/sls/api-publica.json').write_text(
        json.dumps({'versão': 1, 'itens': itens}, ensure_ascii=False, indent=2) + '\n')
    regras = regras_api(itens)
    caminho = ROOT / 'vscode/syntaxes/santafe.tmLanguage.json'
    grammar = json.loads(caminho.read_text())
    repo = grammar['repository']
    repo['constante'] = {'match': BEFORE + r'_(?:G|AMBIENTE|VERSÃO)' + AFTER, 'name': 'support.constant.santafe'}
    repo['função-da-biblioteca'] = {'patterns': regras}
    repo['função']['captures']['1']['name'] = 'storage.type.function.santafe'
    repo['declaração-anônima'] = {'match': BEFORE + 'função' + AFTER, 'name': 'storage.type.function.santafe'}
    if {'include': '#declaração-anônima'} not in grammar['patterns']:
        grammar['patterns'].insert(grammar['patterns'].index({'include': '#palavra-reservada'}), {'include': '#declaração-anônima'})
    caminho.write_text(json.dumps(grammar, ensure_ascii=False, indent=2) + '\n')
    caminho = ROOT / 'sublime/Santafe.sublime-syntax'
    texto = caminho.read_text()
    texto = re.sub(r'^  funcao_global:.*\n', '', texto, flags=re.M)
    inicio = texto.index('  código:\n')
    fim = texto.index('  comentários:\n', inicio)
    texto = texto[:inicio] + '''  código:
    - include: comentários
    - include: declarações
    - include: gabaritos
    - include: colares
    - include: números
    - match: '{{ident_before}}função{{ident_break}}'
      scope: storage.type.function.santafe
    - match: '{{palavra_reservada}}'
      scope: keyword.control.santafe
    - include: api-pública
    - match: '(?:\\.\\.|//|<<|>>|==|~=|<=|>=|[+\\-*/%^#=<>~&|])'
      scope: keyword.operator.santafe
    - match: '[{}()\\[\\],;:]'
      scope: punctuation.separator.santafe

  api-pública:
''' + yaml_regras(regras) + '\n\n' + texto[fim:]
    texto = texto.replace('keyword.declaration.function.santafe', 'storage.type.function.santafe')
    caminho.write_text(texto)
    print('Realce de API gerado:', len(itens), 'entradas')


if __name__ == '__main__':
    principal()
