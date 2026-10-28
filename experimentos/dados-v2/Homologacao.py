"""Homologação no Sublime real, restrita a fixtures temporárias."""
import json
from pathlib import Path
import time
import traceback
import sublime
import sublime_plugin
from . import Realce

def confira(ok, detalhe):
    if not ok: raise AssertionError(detalhe)

class SantafeDadosConteudoCommand(sublime_plugin.TextCommand):
    def run(self, edit, text):
        confira(Path(self.view.file_name()).parent.name.startswith('santafe-dados2-host-'), 'arquivo fora do laboratório')
        self.view.replace(edit, sublime.Region(0,self.view.size()), text)

class SantafeDadosHomologueCommand(sublime_plugin.WindowCommand):
    def run(self):
        root = Path(self.window.folders()[0])
        confira(root.name.startswith('santafe-dados2-host-'), 'janela não é de laboratório')
        from LSP.plugin.core.registry import windows
        from LSP.plugin.core.protocol import Request
        file = root / 'visual.fé'; source = file.read_text()
        view = self.window.open_file(str(file))
        result = {'editor': 'Sublime Text ' + sublime.version(), 'testes': [], 'falhas': []}
        deadline = time.monotonic() + 45
        touched = {view.id(): (view, source)}
        def grave():
            result['resultado'] = 'falhou' if result['falhas'] else 'ok'
            (root/'sublime-resultado.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
        def falha(error):
            result['falhas'].append(str(error)); grave()
            def restore_buffers():
                for buffer, text in touched.values():
                    if buffer.is_valid():
                        buffer.run_command('santafe_dados_conteudo', {'text': text})
            sublime.set_timeout(restore_buffers, 0)
        def pos(text, last=False):
            offset = source.rfind(text) if last else source.find(text); before = source[:offset]
            return {'line': before.count('\n'), 'character': len(before.rsplit('\n', 1)[-1].encode('utf-16-le')) // 2}
        def protocolo():
            try:
                listener = windows.listener_for_view(view)
                sessions = list(listener.session_views_async()) if listener else []
                sv = next((s for s in sessions if s.session.config.name == 'Santafé Dados'
                           and s.has_capability_async('renameProvider')), None)
                if not sv:
                    confira(time.monotonic() < deadline, 'SLS candidato não anexou à view')
                    sublime.set_timeout_async(protocolo, 100); return
                session = sv.session; result['sessão'] = session.config.name
                td = {'textDocument': {'uri': file.as_uri()}}
                sequence = [
                    ('textDocument/definition', {**td, 'position': pos('saudação', True)},
                     lambda r: r and r['range']['start']['line'] == 1),
                    ('textDocument/rename', {**td, 'position': pos('variável'), 'newName': 'posição'},
                     lambda r: len(r['documentChanges'][0]['edits']) >= 6 and all(
                         e['range']['start']['line'] != 9 for e in r['documentChanges'][0]['edits'])),
                    ('textDocument/documentSymbol', td, lambda r: any(s['name'] == 'lista' for s in r)),
                    ('textDocument/completion', {**td, 'position': pos('mostre')},
                     lambda r: any(s['label'] == 'mostre' for s in r)),
                    ('textDocument/semanticTokens/full', td, lambda r: len(r['data']) > 0),
                ]
                def next_request():
                    if not sequence:
                        sublime.set_timeout(lambda: view.run_command('append', {'characters': '\nlocal =\n'}), 0)
                        sublime.set_timeout_async(check_error, 500); return
                    method, params, check = sequence.pop(0)
                    def receive(response):
                        try:
                            confira(check(response), (method, response))
                            result['testes'].append(method); next_request()
                        except Exception: falha(traceback.format_exc())
                    session.send_request_async(Request(method, params, view), receive, falha)
                def check_error():
                    try:
                        diagnostics = session.diagnostics.get_diagnostics_for_uri(file.as_uri())
                        if not diagnostics:
                            confira(time.monotonic() < deadline, 'diagnóstico incremental ausente')
                            sublime.set_timeout_async(check_error, 100); return
                        result['testes'].append('diagnóstico incremental pelo cliente LSP instalado')
                        sublime.set_timeout(restore, 0)
                    except Exception: falha(traceback.format_exc())
                def restore():
                    view.run_command('undo'); Realce.atualize(view)
                    data=self.window.open_file(str(root/'exemplo.onfé'))
                    sublime.set_timeout(lambda: prepare_onfe(data),100)
                def prepare_onfe(data):
                    if data.is_loading():
                        sublime.set_timeout(lambda: prepare_onfe(data),100); return
                    touched[data.id()] = (data, (root/'exemplo.onfé').read_text())
                    data.assign_syntax('Packages/SantafeDados/ONFE.tmLanguage')
                    data.run_command('santafe_dados_conteudo', {'text':touched[data.id()][1]})
                    sublime.set_timeout_async(lambda: wait_onfe_open(data),300)
                def wait_onfe_open(data):
                    try:
                        listener=windows.listener_for_view(data)
                        svs=list(listener.session_views_async()) if listener else []
                        uri=listener.get_uri() if listener else ''
                        opened=any(uri in s.session.diagnostics._diagnostics for s in svs)
                        if not opened:
                            confira(time.monotonic()<deadline,'ONFÉ não abriu no cliente LSP')
                            sublime.set_timeout_async(lambda: wait_onfe_open(data),100); return
                        ds=[d for s in svs for d in s.session.diagnostics.get_diagnostics_for_uri(uri)]
                        confira(not ds, 'ONFÉ válido diagnosticado como inválido')
                        result['testes'].append('ONFÉ: abertura válida pelo cliente LSP')
                        sublime.set_timeout(lambda: data.run_command('santafe_dados_conteudo',
                            {'text':touched[data.id()][1]+'\nimporte "nao-execute"'}),0)
                        sublime.set_timeout_async(lambda: check_onfe(data),500)
                    except Exception: falha(traceback.format_exc())
                def check_onfe(data):
                    try:
                        listener=windows.listener_for_view(data)
                        svs=list(listener.session_views_async()) if listener else []
                        ds=[d for s in svs for d in s.session.diagnostics.get_diagnostics_for_uri(listener.get_uri())]
                        if not ds:
                            confira(time.monotonic()<deadline,'ONFÉ não diagnosticado pelo Sublime')
                            sublime.set_timeout_async(lambda: check_onfe(data),100); return
                        result['testes'].append('ONFÉ: diagnóstico incremental de código proibido')
                        def restore_onfe():
                            data.run_command('santafe_dados_conteudo', {'text':touched[data.id()][1]})
                            sublime.set_timeout_async(lambda: check_clean(data),500)
                        sublime.set_timeout(restore_onfe,0)
                    except Exception: falha(traceback.format_exc())
                def check_clean(data):
                    try:
                        ds=[]
                        for buffer in (view,data):
                            listener=windows.listener_for_view(buffer)
                            ds.extend(d for s in listener.session_views_async()
                                for d in s.session.diagnostics.get_diagnostics_for_uri(listener.get_uri()))
                        if ds:
                            confira(time.monotonic()<deadline,'diagnóstico obsoleto após restaurar os exemplos')
                            sublime.set_timeout_async(lambda: check_clean(data),100); return
                        result['testes'].append('código e ONFÉ: diagnósticos limpos após correção')
                        sublime.set_timeout(lambda: self.window.focus_view(view),0); grave()
                    except Exception: falha(traceback.format_exc())
                next_request()
            except Exception: falha(traceback.format_exc())
        def visual():
            try:
                if view.is_loading():
                    sublime.set_timeout(visual, 100); return
                view.assign_syntax('Packages/SantafeDados/Santafe-Dados.sublime-syntax')
                view.settings().set('santafe_paleta_embutida', 'suave')
                tokens = Realce.tokens_nativos(view, source)
                def at(text):
                    offset = source.index(text)
                    return next((s for a, b, s in tokens if a <= offset < b), '')
                for text, scope in [('prefixo-', 'string'), ('-final', 'string'),
                                    ('retomado', 'comment'), ('const', 'keyword.declaration')]:
                    confira(scope in at(text), (text, at(text)))
                confira(not at('®variável permanece'), 'colar bruto interpolado')
                confira(Realce.aplique(view, source, view.change_count(), tokens), 'realce não aplicado')
                for text in ('®variável /', 'Ⓡvariável', 'Ⓡ{saudação'):
                    scope = view.scope_name(source.index(text))
                    confira('interpolation' in scope, (text, scope))
                    style = view.style_for_scope(scope)
                    confira(style.get('foreground', '').lower() == '#fd971f' and not style.get('italic'), (text, style))
                result['testes'].append('gramáticas nativas: concatenação HTML/JS, bruto e gabaritos')
                result['estilos'] = {key: view.style_for_scope(Realce.escopo_visual(view, at(key)))
                                     for key in ('prefixo-', 'retomado')}
                sublime.set_timeout_async(protocolo, 300)
            except Exception: falha(traceback.format_exc())
        sublime.set_timeout(visual, 300)
