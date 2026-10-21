"""Executar no plugin_host real por comando da homologação, optimize=0.

O comando atua somente na janela do projeto temporário. Não grava documentos.
"""
import json
from pathlib import Path
import time
import traceback
import sublime
from LSP.plugin.core.registry import windows
from LSP.plugin.core.protocol import Request
from Santafe.Santafe import sls_oferece, SantafeConclusões


def execute(window, output):
    root=Path(window.folders()[0])
    if not root.name.startswith('santafe-host-sublime-'):
        raise RuntimeError('a janela deve ser o projeto temporário')
    source='local função somar(a,b)\nretorne a+b\nfim\nlocal variável=1\nlocal variável=2\nmostre(`®variável Ⓡvariável Ⓡ{somar(variável,2)}`)\nlocal página=[[<b title="antes]] .. variável .. [[depois">Oi</b>]]\nmostre(somar(1,2))\n'
    file=root/'ensaio.fé'; file.write_text(source)
    view=window.open_file(str(file))
    result={'editor':'Sublime Text '+sublime.version(),'testes':[],'falhas':[]}
    deadline=time.monotonic()+20

    def grave():
        result['resultado']='falhou' if result['falhas'] else 'ok'
        Path(output).write_text(json.dumps(result,ensure_ascii=False,indent=2))

    def falha(error):
        result['falhas'].append(str(error)); grave()

    def posição(trecho,ultimo=False):
        offset=source.rfind(trecho) if ultimo else source.find(trecho)
        before=source[:offset]; line=before.count('\n'); text=before.rsplit('\n',1)[-1]
        return {'line':line,'character':len(text.encode('utf-16-le'))//2}

    def pronto():
        try:
            if view.is_loading():
                sublime.set_timeout_async(pronto,100); return
            listener=windows.listener_for_view(view)
            svs=list(listener.session_views_async()) if listener else []
            sv=next((s for s in svs if s.session.config.name=='Santafé' and s.has_capability_async('renameProvider')),None)
            if not sv:
                if time.monotonic()>deadline: raise RuntimeError('SLS não anexou à view no prazo')
                sublime.set_timeout_async(pronto,100); return
            session=sv.session
            assert sls_oferece(view,'completionProvider')
            assert SantafeConclusões().on_query_completions(view,'som',[0]) is None
            result['testes'].append('fallback desativado somente na sessão ativa')
            td={'textDocument':{'uri':file.as_uri()}}
            sequence=[
                ('textDocument/definition',{**td,'position':posição('somar',True)},lambda r:bool(r) and r['range']['start']['line']==0),
                ('textDocument/references',{**td,'position':posição('variável'),'context':{'includeDeclaration':True}},lambda r:len(r)>=4),
                ('textDocument/rename',{**td,'position':posição('variável'),'newName':'posição'},lambda r:len(r['documentChanges'][0]['edits'])>=4),
                ('textDocument/documentSymbol',td,lambda r:any(s['name']=='somar' for s in r)),
                ('textDocument/formatting',{**td,'options':{'tabSize':2,'insertSpaces':True}},lambda r:any(e['newText']=='  ' for e in r)),
                ('textDocument/semanticTokens/full',td,lambda r:len(r['data'])>0),
            ]
            def próximo():
                if not sequence:
                    result['testes'].append('requisições pelo transporte do pacote LSP instalado')
                    grave(); return
                method,params,check=sequence.pop(0)
                def recebeu(response):
                    try:
                        assert check(response),(method,response)
                        result['testes'].append(method); próximo()
                    except Exception: falha(traceback.format_exc())
                session.send_request_async(Request(method,params,view),recebeu,falha)
            próximo()
        except Exception: falha(traceback.format_exc())
    sublime.set_timeout_async(pronto,300)
