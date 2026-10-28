#!/usr/bin/env python3
"""Somente fixtures e configurações em diretório temporário novo."""
import json
from pathlib import Path
import shutil
import tempfile
ROOT=Path(__file__).resolve().parents[2]
P=Path(tempfile.mkdtemp(prefix='santafe-dados2-host-'))
for d in ('perfil/User','extensoes','.vscode'): (P/d).mkdir(parents=True)
shutil.copyfile(ROOT/'experimentos/dados-v2/visual.fé',P/'visual.fé')
shutil.copyfile(ROOT/'experimentos/dados-v1/exemplo.onfé',P/'exemplo.onfé')
settings={'security.workspace.trust.enabled':False,'workbench.colorTheme':'Monokai','window.zoomLevel':0,
          'workbench.startupEditor':'none','workbench.welcomePage.experimentalOnboarding':False,
          'editor.fontSize':15,'editor.minimap.enabled':False,'editor.semanticHighlighting.enabled':True,
          'files.associations':{'*.fé':'santafe-dados'},'santafeDados.highlight.embeddedPalette':'suave',
          'santafeDados.languageServer.command':'/bin/sh',
          'santafeDados.languageServer.scopeWarnings':True,
          'santafeDados.languageServer.args':[str(ROOT/'experimentos/dados-v2/santafe-sls-dados')]}
(P/'perfil/User/settings.json').write_text(json.dumps(settings,ensure_ascii=False,indent=2))
project={'folders':[{'path':str(P)}],'settings':{'color_scheme':'Monokai.sublime-color-scheme',
    'font_size':15,'santafe_paleta_embutida':'suave','LSP':{
    'Santafé':{'enabled':False},'Santafé Dados':{'enabled':True,'command':['/bin/sh',str(ROOT/'experimentos/dados-v2/santafe-sls-dados')],
    'selector':'source.santafe-dados | source.onfe','schemes':['file','buffer'],
    'initializationOptions':{'avisosEscopo':True}}}}}
(P/'dados.sublime-project').write_text(json.dumps(project,ensure_ascii=False,indent=2))
print(P)
