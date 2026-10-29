"""Execute por runpy no Sublime. SANTAFE_TESTE_CONCAT_SAIDA define o relatório."""
import importlib
import json
import os
import runpy
from pathlib import Path
import sublime

if not __debug__:
    raise RuntimeError('Execute com compile(..., optimize=0): o plugin_host usa Python -O.')

R = importlib.import_module('Santafe.Realce')
recorte = importlib.import_module('Santafe.bibliotecas.realce_embutido').recorte
casos = runpy.run_path(str(Path(__file__).with_name('casos_concatenacoes.py')))['casos']()
janela = sublime.active_window()
view = janela.new_file()
view.set_scratch(True)
view.assign_syntax('Packages/Santafe/Santafe.sublime-syntax')
fonte = ''
for caso in casos:
    caso['offset'] = len(fonte)
    fonte += caso['fonte'] + '\n\n'
view.run_command('append', {'characters': fonte})

def confira():
    R.atualize(view)
    estado = R.ESTADOS.get(view.id(), {})
    tokens = estado.get('tokens', [])
    falhas = []
    for caso in casos:
        inicio = caso['offset'] + caso['fonte'].index(caso['trecho'])
        for p in range(inicio, inicio + len(caso['trecho'])):
            escopos = [s for a,b,s in tokens if a <= p < b]
            if (caso['tem'] and not any(caso['tem'] in s for s in escopos)) or (not caso['tem'] and escopos):
                falhas.append(dict(nome=caso['nome'], ponto=p, escopos=escopos))
                break
    partes = [p for l in recorte(fonte)[0] for p in l['partes'] if not p.get('buraco')]
    assert all(any(p['inicio'] <= a < b <= p['fim'] for p in partes) for a,b,s in tokens)
    assert R.tokens_nativos(view, fonte, lambda: True) == []
    assert R.tokens_nativos(view, 'x'*(R.LIMITE+1)) == []
    assert not R.aplique(view, fonte, view.change_count()-1, tokens)
    cores = {}
    for tema in ['Monokai', 'Mariana', 'Celeste', 'Breakers', 'Sixteen']:
        view.settings().set('color_scheme', 'Packages/Color Scheme - Default/'+tema+'.sublime-color-scheme')
        R.aplique(view, fonte, view.change_count(), tokens)
        estado = R.ESTADOS[view.id()]
        assert estado['chaves'], 'regiões não aplicadas em '+tema
        assert all(view.get_regions(k) for k in estado['chaves'])
        estilo = view.style_for_scope('string.quoted.double.html meta.santafe-embedded')
        cores[tema] = estilo
        assert estilo.get('background') != view.style_for_scope('string.quoted.double.html').get('background'), tema
    resultado = dict(build=sublime.version(), pacote=json.loads(sublime.load_resource('Packages/Santafe/package-metadata.json'))['version'],
                     casos=len(casos), tokens=len(tokens), falhas=falhas, cores=cores)
    # Alteração real: o listener deve descartar as cores anteriores sem uma
    # chamada explícita de atualize(). Também exerce cancelamento por versão.
    view.run_command('select_all')
    view.run_command('insert', {'characters': 'local comum = "texto"'})
    def apos_edicao():
        novo = R.ESTADOS.get(view.id())
        assert novo and novo['versao'] == view.change_count() and not novo['tokens'] and not novo['chaves']
        resultado['edicao_e_limpeza'] = True
        destino = os.environ.get('SANTAFE_TESTE_CONCAT_SAIDA')
        if destino:
            Path(destino).write_text(json.dumps(resultado, ensure_ascii=False, indent=2))
        R.limpe(view)
        assert view.id() not in R.ESTADOS
        view.close()
        assert not falhas, falhas
        print('Sublime real: {} concatenações, isolamento, edição, cancelamento e cinco temas: ok'.format(len(casos)))
    sublime.set_timeout(apos_edicao, 600)
sublime.set_timeout(confira, 1200)
