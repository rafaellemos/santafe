"""Ensaio pelo host real: só abre/edita buffers do laboratório indicado.

Sem captura de tela, comandos de sistema ou execução do arquivo Fé.
"""
import json
import time
import traceback
import sys
from pathlib import Path
import sublime
import sublime_plugin
from . import Realce

PACKAGE=Path(__file__).parent.name
CONFIG=json.loads((Path(__file__).parent/'laboratorio.json').read_text())
LAB=Path(CONFIG['diretorio'])
REPORT={'editor':sublime.version(),'grupos':[],'resultado':'falhou',
        'python_otimizacao':sys.flags.optimize,
        'python':sys.version,
        'limite':'API nativa de escopos/estilos/regiões; pixels não inspecionados',
        'isolamento':PACKAGE,'kit_sha256':CONFIG['hashes']}
START=time.monotonic()
DONE=False

def ensure(value,detail='condição não atendida'):
    if not value:raise AssertionError(detail)

class SantafeDados9BufferCommand(sublime_plugin.TextCommand):
    def run(self,edit,text):
        ensure(self.view.file_name() and Path(self.view.file_name()).resolve().parent==LAB,'fora do laboratório')
        self.view.replace(edit,sublime.Region(0,self.view.size()),text)

def save():
    (LAB/'sublime-dados9-resultado.json').write_text(json.dumps(REPORT,ensure_ascii=False,indent=2))

def check(view):
    source=view.substr(sublime.Region(0,view.size()))
    original=(LAB/'visual.fé').read_text();ensure(source==original,'fixture alterado antes do ensaio')
    syntax='Packages/'+PACKAGE+'/Santafe-Dados.sublime-syntax'
    view.assign_syntax(syntax)
    view.settings().set('color_scheme','Packages/'+PACKAGE+'/Dados9Host.sublime-color-scheme')
    view.settings().set('santafe_paleta_embutida','suave')
    view.settings().set('font_size',15)
    scope=lambda word:view.scope_name(source.index(word))
    group=lambda name:REPORT['grupos'].append(name)
    try:
        try:ensure(False,'sentinela do próprio ensaio')
        except AssertionError:REPORT['sentinela_validada']=True
        else:raise RuntimeError('verificações do harness não estão sendo executadas')
        ensure(view.syntax().scope==CONFIG['scope'])
        ensure('raw' in scope('®variável e Ⓡ{título}') and 'interpolation' not in scope('®variável e Ⓡ{título}'))
        ensure('raw' in scope('Um fechamento'))
        ensure('constant.numeric' in scope('42') and 'string' not in scope('42'))
        ensure('constant.numeric' in scope('1, nulo') and 'string' not in scope('1, nulo'))
        ensure('comment.block' in scope('isto não abre'))
        group('delimitadores por nível, listas e comentários sem vazamento')
        styles={}
        for word in ('®variável /','Ⓡvariável /','Ⓡ{título ..'):
            pos=source.index(word);sc=view.scope_name(pos)
            ensure('interpolation' in sc,(word,sc))
            sty=view.style_for_scope(sc);ensure(sty.get('foreground','').lower()=='#fd971f',(word,sty))
            ensure(not sty.get('italic',False),(word,sty))
            styles[word]=sty
        ensure('string.quoted.other.gabarito' not in scope('título .. "!"'))
        group('® e Ⓡ laranja normal, expressão interna é código')
        tokens=Realce.tokens_nativos(view,source)
        REPORT['tokens']=tokens
        def embedded(word):
            pos=source.index(word)
            return next((s for a,b,s in tokens if a<=pos<b),'')
        for word in ('prefixo-','-final'):ensure('string' in embedded(word),(word,embedded(word)))
        ensure('comment' in embedded('retomado'))
        ensure('keyword.declaration' in embedded('const pronto'),embedded('const pronto'))
        ensure('entity.other.attribute-name' in embedded('data-id'))
        ensure(not embedded('®variável e Ⓡ{título}'))
        ensure(not embedded('mostre(página'))
        group('HTML automático e JS etiquetado atravessam concatenações')
        ensure(Realce.aplique(view,source,view.change_count(),tokens))
        state=Realce.ESTADOS[view.id()];ensure(state['chaves'])
        ensure(sum(len(view.get_regions(k)) for k in state['chaves'])>10)
        for word in ('prefixo-','retomado','data-id'):
            visual=Realce.escopo_visual(view,embedded(word))
            ensure('meta.santafe-soft-escura' in visual,(visual,view.style()))
            styles[word]=view.style_for_scope(visual)
            ensure(styles[word].get('background')!=view.style_for_scope(embedded(word)).get('background'))
        group('regiões visuais aplicadas com paleta suave')
        # Edição do fixture apenas em memória, depois restauração.
        broken=source.replace('local bruto = [==[','local bruto = [===[',1)
        view.run_command('santafe_dados8_buffer',{'text':broken})
        ensure('raw' in view.scope_name(broken.index('local após')))
        view.run_command('santafe_dados8_buffer',{'text':source})
        ensure('string' not in view.scope_name(source.index('local após')))
        group('realce incremental: fechamento incompatível e recuperação')
        REPORT['escopos']={w:scope(w) for w in ('®variável e Ⓡ{título}','®variável /','Ⓡvariável /','Ⓡ{título ..','título .. "!"','1, nulo','42')}
        REPORT['estilos']=styles;REPORT['tokens']=tokens
        # ONFÉ em painel oculto: sintaxe real, não um mock.
        panel=view.window().create_output_panel('santafe_dados8_onfe_qa')
        try:
            panel.assign_syntax('Packages/'+PACKAGE+'/ONFE.tmLanguage')
            data=(LAB/'exemplo.onfé').read_text()
            panel.run_command('append',{'characters':data})
            for word in ('®variável e','Segunda linha','aceita ]=]'):
                sc=panel.scope_name(data.index(word));ensure('string' in sc and 'interpolation' not in sc,sc)
            ensure('string' not in panel.scope_name(data.index('1, nulo')))
            group('ONFÉ: colares brutos por nível, curingas literais e lista')
        finally:view.window().destroy_output_panel('santafe_dados8_onfe_qa')
        REPORT['resultado']='ok'
    except Exception:
        REPORT['falha']=traceback.format_exc()
    finally:
        if view.substr(sublime.Region(0,view.size()))!=original:
            view.run_command('santafe_dados8_buffer',{'text':original})
        Realce.atualize(view)
        save()

def attempt():
    global DONE
    if DONE:return
    if time.monotonic()-START>60:
        REPORT['falha']='laboratório não abriu em 60s';save();DONE=True;return
    for win in sublime.windows():
        for view in win.views():
            if view.file_name() and Path(view.file_name()).resolve()==LAB/'visual.fé' and not view.is_loading():
                DONE=True;check(view);return
    sublime.set_timeout(attempt,300)

def plugin_loaded():
    ensure(LAB.name.startswith('santafe-dados8-host-') and LAB.is_dir())
    # Os kits originais usam a mesclagem por mesmo nome Monokai. Para isolar
    # o laboratório sem afetar outros buffers, materializamos essa mesclagem
    # sob nome próprio; .sublime-color-scheme não possui uma chave extends.
    theme=Path(__file__).parent/'Dados9Host.sublime-color-scheme'
    custom=json.loads(theme.read_text())
    if 'extends' in custom:
        base=sublime.decode_value(sublime.load_resource(custom['extends']))
        base['rules'].extend(custom['rules'])
        base['name']='Monokai — dados.9 (laboratório isolado)'
        theme.write_text(json.dumps(base,ensure_ascii=False,indent=2))
    sublime.set_timeout(attempt,500)
