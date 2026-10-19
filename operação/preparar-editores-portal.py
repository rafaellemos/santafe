#!/usr/bin/env python3
"""Prepara apenas página, pacotes e catálogos dos editores; não instala nada."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

VSIX = "santafe-vscode-1.0.6.vsix"
MANUAL = "Santafe.sublime-package"
CONTROLE = "Santafe-1.0.13.sublime-package"
ARQUIVOS = (f"baixar/{VSIX}", f"baixar/{MANUAL}", f"sublime/{CONTROLE}", "sublime/packages.json")


def soma(caminho):
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def valide_pacotes(payload):
    with zipfile.ZipFile(payload / "baixar" / VSIX) as z:
        assert z.testzip() is None, "VSIX corrompido"
        assert json.loads(z.read("extension/package.json"))["version"] == "1.0.6"
        for nome in ("realce-embutido.js", "realce-vscode.js", "aparencia.js", "paletas.json", "vendor/vscode-oniguruma/release/onig.wasm"):
            assert "extension/" + nome in z.namelist(), nome
        sintaxe = json.loads(z.read("extension/syntaxes/santafe.tmLanguage.json"))
        regras = sintaxe["repository"]["interpolação"]["patterns"]
        assert regras[0]["begin"] == r"[®Ⓡ]\{"
        assert "variable.parameter.santafe" in regras[1]["name"]
    with zipfile.ZipFile(payload / "baixar" / MANUAL) as manual, \
            zipfile.ZipFile(payload / "sublime" / CONTROLE) as controle:
        assert manual.testzip() is None and controle.testzip() is None
        assert json.loads(manual.read("package-metadata.json"))["version"] == "1.0.13"
        assert "package-metadata.json" not in controle.namelist()
        assert set(manual.namelist()) == set(controle.namelist()) | {"package-metadata.json"}
        for nome in controle.namelist():
            assert manual.read(nome) == controle.read(nome), nome
        for nome in ("Default.sublime-keymap", "HTML-Santafe.sublime-syntax", "JavaScript-Santafe.sublime-syntax", "Realce.py", "realce_embutido.py"):
            assert nome in controle.namelist(), nome
        for tema in ("Monokai", "Mariana", "Celeste", "Breakers", "Sixteen"):
            regras = json.loads(controle.read(f"ColorSchemes/{tema}.sublime-color-scheme"))["rules"]
            assert regras[0] == {"scope": "meta.santafe-embedded", "background": "#00000001"}
            assert len([r for r in regras if r['scope'].startswith('meta.santafe-soft-')]) == 36
            assert any(r.get('foreground') == '#FD971F' and r.get('font_style') == '' for r in regras)
        sintaxe = controle.read("Santafe.sublime-syntax").decode("utf-8")
        assert "[®Ⓡ]" in sintaxe and "keyword.operator.interpolation.santafe" in sintaxe
    catalogo = json.loads((payload / "sublime/packages.json").read_text())
    assert catalogo["schema_version"] == "4.0.0"
    assert len(catalogo["packages"]) == 1
    pacote = catalogo["packages"][0]
    assert pacote["name"] == "Santafe" and len(pacote["releases"]) == 1
    release = pacote["releases"][0]
    assert release["version"] == "1.0.13"
    assert release["url"] == "https://xn--santaf-gva.dev.br/est%C3%A1tico/sublime/" + CONTROLE


def troque_unico(texto, padrao, novo):
    resultado, quantidade = re.subn(padrao, lambda _: novo, texto, flags=re.DOTALL)
    if quantidade != 1:
        raise ValueError(f"Página inesperada: {padrao!r}; ocorrências={quantidade}")
    return resultado


def pagina_atualizada(texto):
    rota = 'ap.rota("GET", "/baixar", função(req, res)'
    if texto.count(rota) != 1:
        raise ValueError("Rota /baixar ausente ou duplicada")
    inicio = texto.index(rota)
    proxima = re.search(r"(?m)^ap\.rota\(", texto[inicio + len(rota):])
    if proxima is None:
        raise ValueError("Não foi possível delimitar a rota /baixar")
    fim = inicio + len(rota) + proxima.start()
    pagina = texto[inicio:fim]
    pagina = troque_unico(pagina, r"<p>Extensão oficial [0-9.]+:.*?</p>",
        '<p>Extensão oficial 1.0.6: realce da API pública, paleta suave opcional para HTML/JS, atributos e comentários preservados entre concatenações, realce de <code>®var</code>, '
        '<code>Ⓡvar</code> e expressões, HTML/JavaScript dentro de colares, conclusões e diagnósticos pelo SLS.</p>')
    pagina = troque_unico(pagina, r"<p>Pacote oficial [0-9.]+ para arquivos.*?</p>",
        '<p>Pacote oficial 1.0.13 para arquivos <code>.fé</code>: realce da API pública, paleta suave opcional para HTML/JS, atributos e comentários preservados entre concatenações, Enter com recuo e <code>fim</code>, '
        'realce dos dois curingas e de HTML/JavaScript em colares, conclusões, execução, integração SLS e Package Control.</p>')
    pagina, total = re.subn(r"santafe-vscode-[0-9]+(?:\.[0-9]+)+\.vsix", VSIX, pagina)
    if total != 2:
        raise ValueError(f"Referências VSIX inesperadas: {total}")
    pagina = troque_unico(pagina, r'href="/estático/baixar/Santafe\.sublime-package(?:\?v=[^"]*)?"',
        'href="/estático/baixar/Santafe.sublime-package?v=1.0.13"')
    notas = '''      <div id="editores-realce" class="card-panel teal lighten-5">
        <strong>Editores atualizados — 18 de outubro de 2026</strong>
        <p>Os curingas <code>®</code> e <code>Ⓡ</code> participam do realce de variáveis e expressões. Para colares multilinha, use <code>local página = --&#91;&#91;html&#93;&#93; &#91;&#91;</code> ou <code>local código = --&#91;&#91;javascript&#93;&#93; &#91;&#91;</code>. Esse realce não altera o núcleo nem acrescenta análise semântica HTML/JS ao SLS.</p>
        <p>Já usa o Sublime? Execute <strong>Package Control: Upgrade Package → Santafe</strong>. No VS Code, instale o VSIX atualizado e recarregue a janela.</p>
        <p>Nos dois editores, escolha <strong>Santafé: Paleta de HTML e JavaScript embutidos</strong> na paleta de comandos. O padrão acompanha o tema. Marcadores e chaves dos gabaritos ficam laranja, sem itálico; o interior da expressão continua código Santafé. No Monokai, <code>função</code> fica ciano e itálico.</p>
      </div>
'''
    if 'id="editores-realce"' in pagina:
        pagina = troque_unico(pagina, r'      <div id="editores-realce".*?</div>\n', notas)
    else:
        marcador = '      <h5 style="margin-top:32px">Instalação</h5>'
        if pagina.count(marcador) != 1:
            raise ValueError("Seção Instalação inesperada")
        pagina = pagina.replace(marcador, notas + "\n" + marcador)
    return texto[:inicio] + pagina + texto[fim:]


def atualize_somas(anterior, novos):
    linhas = []
    vistos = set()
    for linha in anterior.splitlines():
        if not linha.strip():
            continue
        m = re.fullmatch(r"([0-9a-f]{64})  ([^/\\\s]+)", linha)
        if not m or m[2] in vistos:
            raise ValueError("Manifesto SHA256SUMS inválido ou duplicado")
        vistos.add(m[2])
        linhas.append(f"{novos.get(m[2], m[1])}  {m[2]}")
    for nome, resumo in novos.items():
        if nome not in vistos:
            linhas.append(f"{resumo}  {nome}")
    return "\n".join(linhas) + "\n"


def prepare(payload, aplicacao, fonte, estatico, saida):
    valide_pacotes(payload)
    if aplicacao.read_bytes() != (fonte / "sfdev.fé").read_bytes():
        raise ValueError("Aplicação e árvore-fonte diferem; interrompido para preservar alterações locais")
    saida.mkdir(parents=True, exist_ok=True)
    pagina = saida / "sfdev.fé"
    pagina.write_text(pagina_atualizada(aplicacao.read_text(encoding="utf-8")), encoding="utf-8")
    novos = {nome: soma(payload / "baixar" / nome) for nome in (VSIX, MANUAL)}
    somas = saida / "SHA256SUMS"
    somas.write_text(atualize_somas((estatico / "baixar/SHA256SUMS").read_text(), novos))
    plano = [(pagina, aplicacao, "sfdev:sfdev", "0755"),
             (pagina, fonte / "sfdev.fé", "rafael:rafael", "0644")]
    for base, dono in ((estatico, "www-data:www-data"), (fonte, "rafael:rafael")):
        plano += [(payload / item, base / item, dono, "0644") for item in ARQUIVOS]
        plano.append((somas, base / "baixar/SHA256SUMS", dono, "0644"))
    for origem, destino, dono, modo in plano:
        if not destino.parent.is_dir() or destino.is_symlink():
            raise ValueError(f"Destino não é um diretório existente ou é link: {destino}")
        if destino.exists() and not destino.is_file():
            raise ValueError(f"Destino não é arquivo regular: {destino}")
        if destino.name in (VSIX, CONTROLE) and destino.exists() and soma(destino) != soma(origem):
            raise ValueError(f"Artefato versionado já existe com conteúdo diferente: {destino}")
    (saida / "plano.tsv").write_text("".join(
        f"{i:03d}\t{origem}\t{destino}\t{dono}\t{modo}\n"
        for i, (origem, destino, dono, modo) in enumerate(plano)))
    (saida / "antes.sha256.json").write_text(json.dumps({str(dst): soma(dst) if dst.exists() else None
        for _, dst, _, _ in plano}, ensure_ascii=False))
    print("Página, arquivos e catálogo preparados; núcleo e downloads históricos preservados.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for nome in ("payload", "aplicacao", "fonte", "estatico", "saida"):
        parser.add_argument("--" + nome, type=Path, required=True)
    args = parser.parse_args()
    prepare(args.payload, args.aplicacao, args.fonte, args.estatico, args.saida)
