#!/usr/bin/env python3
"""Regressões do preparo: sem instalar nem reiniciar qualquer serviço."""
import importlib.util
import json
from pathlib import Path
import tempfile
import zipfile

RAIZ = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("preparo", RAIZ / "operação/preparar-editores-portal.py")
preparo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preparo)

PAGINA = '''-- Antes da rota: não alterar 2.0.1
ap.rota("GET", "/baixar", função(req, res)
    local conteúdo = [[
      <p>Extensão oficial 1.0: versão anterior.</p>
      <a href="/estático/baixar/santafe-vscode-1.0.0.vsix">VSIX</a>
      <p>Pacote oficial 1.0.7 para arquivos antigos.</p>
      <a href="/estático/baixar/Santafe.sublime-package">Sublime</a>
      <h5 style="margin-top:32px">Instalação</h5>
      <p>Instale santafe-vscode-1.0.0.vsix.</p>
      <a href="santafe-2.0.1.tar.gz">Núcleo 2.0.1</a>
    ]]
fim)

ap.rota("GET", "/outra", função(req, res)
    mostre("não alterar")
fim)
'''


def rejeita(acao):
    try:
        acao()
    except ValueError:
        return
    raise AssertionError("alteração insegura não foi recusada")


def artefatos_historicos(payload):
    """Fixtures explícitos do publicador antigo; nunca são pacotes de entrega.

    A regressão não pode depender de dist/ ignorado pelo Git ou relabelar o
    código novo como uma versão histórica. O pacote corrente tem testes próprios.
    """
    with zipfile.ZipFile(payload/'baixar'/preparo.VSIX,'w') as z:
        z.writestr('extension/package.json',json.dumps({'version':'1.0.6'}))
        z.writestr('extension/syntaxes/santafe.tmLanguage.json',json.dumps({
            'repository':{'interpolação':{'patterns':[
                {'begin':r'[®Ⓡ]\{'},{'name':'variable.parameter.santafe'}]}}}))
        for name in ('realce-embutido.js','realce-vscode.js','aparencia.js','paletas.json','vendor/vscode-oniguruma/release/onig.wasm'):
            z.writestr('extension/'+name,'fixture do publicador histórico; não executar')
    data={name:b'fixture do publicador historico; nao executar' for name in
          ('Default.sublime-keymap','HTML-Santafe.sublime-syntax','JavaScript-Santafe.sublime-syntax','Realce.py','realce_embutido.py')}
    data['Santafe.sublime-syntax']='[®Ⓡ] keyword.operator.interpolation.santafe'.encode()
    rules=[{'scope':'meta.santafe-embedded','background':'#00000001'},
           {'scope':'keyword.operator.interpolation.santafe','foreground':'#FD971F','font_style':''}]
    rules += [{'scope':'meta.santafe-soft-'+str(i),'foreground':'#aaaaaa'} for i in range(36)]
    for theme in ('Monokai','Mariana','Celeste','Breakers','Sixteen'):
        data['ColorSchemes/'+theme+'.sublime-color-scheme']=json.dumps({'rules':rules}).encode()
    for name,folder in ((preparo.MANUAL,'baixar'),(preparo.CONTROLE,'sublime')):
        with zipfile.ZipFile(payload/folder/name,'w') as z:
            for entry,content in data.items(): z.writestr(entry,content)
            if name==preparo.MANUAL:
                z.writestr('package-metadata.json',json.dumps({'version':'1.0.13'}))
    (payload/'sublime/packages.json').write_text(json.dumps({'schema_version':'4.0.0','packages':[
        {'name':'Santafe','releases':[{'version':'1.0.13','url':'https://xn--santaf-gva.dev.br/est%C3%A1tico/sublime/'+preparo.CONTROLE}]}]}))


with tempfile.TemporaryDirectory(prefix="santafe-publicador-teste-") as temporario:
    raiz = Path(temporario)
    payload = raiz / "payload"
    fonte, estatico = raiz / "fonte", raiz / "estatico"
    for base in (payload, fonte, estatico):
        for pasta in ("baixar", "sublime"):
            (base / pasta).mkdir(parents=True)
    artefatos_historicos(payload)
    app = raiz / "sfdev.fé"
    app.write_text(PAGINA)
    (fonte / "sfdev.fé").write_text(PAGINA)
    somas = "0" * 64 + "  santafe-2.0.1.tar.gz\n" + "1" * 64 + "  Santafe.sublime-package\n"
    (estatico / "baixar/SHA256SUMS").write_text(somas)
    saida = raiz / "preparado"
    preparo.prepare(payload, app, fonte, estatico, saida)
    assert app.read_text() == PAGINA == (fonte / "sfdev.fé").read_text()
    assert (estatico / "baixar/SHA256SUMS").read_text() == somas
    novo = (saida / "sfdev.fé").read_text()
    assert preparo.pagina_atualizada(novo) == novo, "o patch precisa ser idempotente"
    assert novo.split('ap.rota("GET", "/outra"')[1] == PAGINA.split('ap.rota("GET", "/outra"')[1]
    assert "santafe-2.0.1.tar.gz" in novo
    assert novo.count("]]") == PAGINA.count("]]"), "HTML não pode encerrar o colar da página"
    assert "®var" in novo and "Ⓡvar" in novo
    manifest = (saida / "SHA256SUMS").read_text()
    assert somas.splitlines()[0] in manifest
    assert preparo.soma(payload / "baixar" / preparo.MANUAL) in manifest
    assert len((saida / "plano.tsv").read_text().splitlines()) == 12
    rejeita(lambda: preparo.pagina_atualizada(PAGINA.replace("Extensão oficial", "Outro conteúdo")))
    rejeita(lambda: preparo.atualize_somas("inválido\n", {}))
    (fonte / "sfdev.fé").write_text(PAGINA + "-- edição local\n")
    rejeita(lambda: preparo.prepare(payload, app, fonte, estatico, saida))
    (fonte / "sfdev.fé").write_text(PAGINA)
    (estatico / "baixar" / preparo.VSIX).write_bytes("outra versão imutável".encode("utf-8"))
    rejeita(lambda: preparo.prepare(payload, app, fonte, estatico, saida))
print("Publicador dos editores: preservação, idempotência, integridade e limites: ok")
