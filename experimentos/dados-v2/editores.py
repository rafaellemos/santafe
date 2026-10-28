#!/usr/bin/env python3
"""Monta extensões completas de laboratório, sem instalar em perfis existentes."""
import json
import os
from pathlib import Path
import runpy
import shutil
import zipfile

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'dist/candidato-dados-v22/editores'
OUT.mkdir(parents=True,exist_ok=True)
os.environ['SANTAFE_EDITORES_OUT']=str(OUT/'gramaticas')
runpy.run_path(str(ROOT/'experimentos/dados-v1/editores.py'))
V=OUT/'vscode'; S=OUT/'SantafeDados'
V.mkdir(exist_ok=True); S.mkdir(exist_ok=True)

for p in (ROOT/'extensões/vscode').rglob('*'):
    rel=p.relative_to(ROOT/'extensões/vscode')
    if not p.is_file() or any(x in rel.parts for x in ('testes','__pycache__','dist')) or p.suffix=='.py': continue
    target=V/rel; target.parent.mkdir(parents=True,exist_ok=True)
    if p.suffix in ('.js','.json'):
        text=p.read_text().replace('"santafe"','"santafe-dados"').replace('"santafe.','"santafeDados.')
        text=text.replace('DIALETO_DADOS = false','DIALETO_DADOS = true')
        text=text.replace('getConfiguration("santafe-dados"','getConfiguration("santafeDados"').replace('"santafeDados.exe"','"santafe.exe"')
        target.write_text(text)
    else: shutil.copyfile(p,target)

manifest=json.loads((V/'package.json').read_text())
manifest.update(name='santafe-dados-experimental',publisher='santafe',displayName='Santafé — candidato dados.22',version='0.0.22',
                description='Laboratório isolado de listas, nulo armazenável, ONFÉ e SLS. Não é uma versão de produção.')
manifest['activationEvents']=['onLanguage:santafe-dados','onLanguage:onfe-experimental']
c=manifest['contributes']
c['configurationDefaults']={'[santafe-dados]':{'editor.semanticHighlighting.enabled':True}}
c['languages'][0]['extensions']=[]
c['languages'][0]['aliases']=['Santafé Dados Experimental']
c['languages'].append({'id':'onfe-experimental','aliases':['ONFÉ Experimental'],'extensions':['.onfé']})
c['grammars'][0]['scopeName']='source.santafe-dados'
c['grammars'].append({'language':'onfe-experimental','scopeName':'source.onfe','path':'./syntaxes/onfe.tmLanguage.json'})
c['configuration']['properties']['santafeDados.languageServer.command']['default']='santafe-sls-dados'
c['configuration']['properties']['santafeDados.languageServer.scopeWarnings']={'type':'boolean','default':False,
    'description':'Avisa sobre nomes sem declaração local visível. Globais dinâmicos continuam válidos; não cria temVar.'}
(V/'package.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
shutil.copyfile(OUT/'gramaticas/santafe-dados.tmLanguage.json',V/'syntaxes/santafe.tmLanguage.json')
p=V/'syntaxes/santafe.tmLanguage.json'; p.write_text(p.read_text().replace('source.santafe.dados','source.santafe-dados'))
shutil.copyfile(OUT/'gramaticas/onfe.tmLanguage.json',V/'syntaxes/onfe.tmLanguage.json')
# ONFÉ compartilha transporte/diagnóstico, nunca os provedores de código.
p=V/'extension.js'; t=p.read_text()
t=t.replace('documento.languageId !== LINGUAGEM','![LINGUAGEM,"onfe-experimental"].includes(documento.languageId)')
t=t.replace('documento.languageId === LINGUAGEM','[LINGUAGEM,"onfe-experimental"].includes(documento.languageId)')
t=t.replace('languageId: LINGUAGEM,','languageId: documento.languageId,')
t=t.replace('clientInfo: { name:', 'initializationOptions: {avisosEscopo:this.configuração().get("scopeWarnings",false)},\n        clientInfo: { name:')
p.write_text(t)

# Kit Sublime em namespace próprio. Preserva o pacote Santafe instalado.
for name in ('Realce.py','realce_embutido.py','paletas.json'):
    text=(ROOT/'extensões/sublime'/name).read_text()
    text=text.replace('DADOS_EXPERIMENTAIS = False','DADOS_EXPERIMENTAIS = True')
    text=text.replace('"source.santafe"','"source.santafe-dados"')
    text=text.replace('SantafeRealceListener','SantafeDadosRealceListener').replace('SantafePaletaEmbutidaCommand','SantafeDadosPaletaEmbutidaCommand')
    text=text.replace('Santafe.sublime-settings','SantafeDados.sublime-settings').replace('santafe_realce_','santafe_dados_realce_')
    (S/name).write_text(text)
syntax=(OUT/'gramaticas/Santafe-Dados.sublime-syntax').read_text()
syntax=syntax.replace('source.santafe.dados','source.santafe-dados')
original=(ROOT/'extensões/sublime/Santafe.sublime-syntax').read_text()
api=original[original.index('  api-pública:'):original.index('  comentários:')]
syntax=syntax.replace('  main:\n','  main:\n    - include: api-pública\n',1)+ '\n'+api
(S/'Santafe-Dados.sublime-syntax').write_text(syntax)
with zipfile.ZipFile(OUT/'gramaticas/Santafe-Dados-Experimental.sublime-package') as z:
    (S/'ONFE.tmLanguage').write_bytes(z.read('ONFE.tmLanguage'))
for p in (ROOT/'extensões/sublime/ColorSchemes').glob('*.sublime-color-scheme'):
    (S/'ColorSchemes').mkdir(exist_ok=True)
    scheme=json.loads(p.read_text())
    scheme['rules'].append({'scope':'source.santafe-dados variable.other.interpolation.santafe, source.santafe-dados punctuation.section.interpolation',
                            'foreground':'#FD971F','font_style':''})
    (S/'ColorSchemes'/p.name).write_text(json.dumps(scheme,ensure_ascii=False,indent=2)+'\n')
(S/'.python-version').write_text('3.8\n')
(S/'SantafeDados.sublime-settings').write_text('{"paleta_embutida":"suave"}\n')
shutil.copyfile(ROOT/'experimentos/dados-v2/Homologacao.py',S/'Homologacao.py')
(S/'LSP-santafe-dados.sublime-settings.example').write_text(json.dumps({
    'clients':{'Santafé Dados':{'enabled':True,'command':['/bin/sh','/CAMINHO/experimentos/dados-v2/santafe-sls-dados'],
    'selector':'source.santafe-dados | source.onfe','schemes':['file','buffer'],
    'initializationOptions':{'avisosEscopo':True}}}},ensure_ascii=False,indent=2)+'\n')
for folder in (V,S):
    (folder/'README.md').write_text('# Santafé — candidato dados.22\n\n'
        'Extensão experimental 0.0.22, separada da edição estável. Não publicada em catálogo.\n\n'
        'Use somente com o núcleo e SLS do pacote dados.22 e um projeto/perfil de laboratório. '
        'Consulte experimentos/dados-v2/LEIA-ME.md no pacote para configurar o iniciador e executar os testes.\n')
    shutil.copyfile(ROOT/'LICENSE',folder/'LICENSE')

# Usa a estrutura VSIX já conferida e substitui somente sua identidade/versão.
with zipfile.ZipFile(OUT/'gramaticas/santafe-dados-experimental-0.0.1.vsix') as old:
    xml=old.read('extension.vsixmanifest').decode().replace('0.0.1','0.0.22')
with zipfile.ZipFile(OUT/'santafe-dados-experimental-0.0.22.vsix','w',zipfile.ZIP_DEFLATED) as z:
    z.writestr('extension.vsixmanifest',xml)
    z.writestr('[Content_Types].xml','<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="json" ContentType="application/json"/><Default Extension="js" ContentType="application/javascript"/><Default Extension="png" ContentType="image/png"/><Default Extension="svg" ContentType="image/svg+xml"/><Default Extension="md" ContentType="text/markdown"/><Default Extension="vsixmanifest" ContentType="text/xml"/></Types>')
    for p in sorted(V.rglob('*')):
        if p.is_file(): z.write(p,'extension/'+str(p.relative_to(V)))
with zipfile.ZipFile(OUT/'SantafeDados.sublime-package','w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(S.rglob('*')):
        if p.is_file(): z.write(p,str(p.relative_to(S)))
print('EDITORES_DADOS_15_OK',OUT)
