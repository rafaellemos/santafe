"""Executar no Sublime real; não altera documentos ou preferências persistentes."""
import importlib
import json
import os
from pathlib import Path
import sublime

if not __debug__:
    raise RuntimeError('Execute com compile(..., optimize=0): o plugin_host usa Python -O.')

R = importlib.import_module('Santafe.Realce')
itens = json.loads(sublime.load_resource('Packages/Santafe/api-publica.json'))['itens']
view = sublime.active_window().new_file()
view.set_scratch(True)
view.assign_syntax('Packages/Santafe/Santafe.sublime-syntax')
linhas = [i['rótulo'] + '()' for i in itens]
extra = '''local função exemplo(valor)
    local redeLocal = importe "rede"
    redeLocal.laço()
    retorne `Olá ®nome Ⓡnome ®{valor + mat.raiz(4)} Ⓡ{valor + tamanho("a")} fim`
fim
local html = `<b class="Ⓡ{valor} fim">®nome</b>`
local html = [[<b class="parte-]] .. nome .. [[-final">Olá</b>]]
local js = --[[javascript]] [[/* parte ]] .. nome .. [[ final */ const n = 3;]]
'''
fonte = '\n'.join(linhas) + '\n' + extra
view.run_command('append', {'characters': fonte})


def confira():
    falhas = []
    p = 0
    for item, linha in zip(itens, linhas):
        scope = view.scope_name(p + len(item['rótulo']) - 1)
        if not any(s in scope for s in ('support.', 'variable.function', 'variable.other.member')):
            falhas.append((item['rótulo'], scope))
        p += len(linha) + 1
    view.settings().set('color_scheme', 'Packages/Color Scheme - Default/Monokai.sublime-color-scheme')
    estilos = {}
    for trecho in ('®nome', 'Ⓡnome', '®{', 'Ⓡ{', 'valor + mat', 'valor + tamanho', 'função'):
        pos = fonte.index(trecho, p)
        scope = view.scope_name(pos)
        estilo = view.style_for_scope(scope)
        estilos[trecho] = dict(escopo=scope, estilo=estilo)
        if trecho.startswith(('®', 'Ⓡ')):
            assert estilo['foreground'].lower() == '#fd971f', (trecho, scope, estilo)
            assert not estilo.get('italic', False), (trecho, estilo)
        elif trecho.startswith('valor'):
            assert 'string.' not in scope, scope
            assert estilo['foreground'].lower() != '#e6db74', estilo
        else:
            assert estilo['foreground'].lower() == '#66d9ef', estilo
            assert estilo.get('italic'), estilo
    # Também dentro de um atributo HTML: código não pode herdar string amarela.
    pos = fonte.index('Ⓡ{valor}', p) + 2
    assert 'string.' not in view.scope_name(pos), view.scope_name(pos)
    R.atualize(view)
    tokens = R.ESTADOS[view.id()]['tokens']
    assert tokens
    cores = {}
    for paleta in ('tema', 'suave'):
        view.settings().set('santafe_paleta_embutida', paleta)
        R.aplique(view, fonte, view.change_count(), tokens)
        scope = R.escopo_visual(view, 'entity.name.tag.html')
        cores[paleta] = view.style_for_scope(scope)['foreground']
        assert R.ESTADOS[view.id()]['chaves']
    assert cores['tema'] != cores['suave'], cores
    assert cores['suave'].lower() == '#9bb5c7', cores
    view.settings().set('santafe_paleta_embutida', 'tema')
    R.aplique(view, fonte, view.change_count(), tokens)
    assert R.escopo_visual(view, 'entity.name.tag.html') == 'entity.name.tag.html meta.santafe-embedded'
    resultado = dict(casos=len(itens), falhas=falhas, estilos=estilos, cores=cores, reversivel=True)
    if os.environ.get('SANTAFE_TESTE_API_SAIDA'):
        Path(os.environ['SANTAFE_TESTE_API_SAIDA']).write_text(json.dumps(resultado, ensure_ascii=False, indent=2))
    view.close()
    assert not falhas, falhas
    print('Sublime real: {} entradas API, cores, gabaritos e paleta reversível: ok'.format(len(itens)))

sublime.set_timeout(confira, 1200)
