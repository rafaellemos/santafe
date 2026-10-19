#!/usr/bin/env python3
"""Regressões do preparo: sem instalar nem reiniciar qualquer serviço."""
import importlib.util
from pathlib import Path
import shutil
import tempfile

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


with tempfile.TemporaryDirectory(prefix="santafe-publicador-teste-") as temporario:
    raiz = Path(temporario)
    payload = raiz / "payload"
    fonte, estatico = raiz / "fonte", raiz / "estatico"
    for base in (payload, fonte, estatico):
        for pasta in ("baixar", "sublime"):
            (base / pasta).mkdir(parents=True)
    shutil.copy2(RAIZ / "extensões/vscode/dist/santafe-1.0.6.vsix", payload / "baixar" / preparo.VSIX)
    for nome in (preparo.MANUAL, preparo.CONTROLE, "packages.json"):
        pasta = "baixar" if nome == preparo.MANUAL else "sublime"
        shutil.copy2(RAIZ / "extensões/sublime/dist" / nome, payload / pasta / nome)
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
