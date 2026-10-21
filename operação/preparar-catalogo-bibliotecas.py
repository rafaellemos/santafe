#!/usr/bin/env python3
"""Constrói catálogo estático curado; nunca publica nem altera o servidor.

Python só é necessário para a manutenção do catálogo, não para quem instala
bibliotecas. A validação/empacotamento usa o próprio cliente Santafé.
"""
import argparse
import hashlib
import html
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
URL = "https://xn--santaf-gva.dev.br/est%C3%A1tico/bibliotecas/v1"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(text):
    p = PurePosixPath(text)
    if not text or str(p) != text or p.is_absolute() or any(x in (".", "..") for x in p.parts):
        raise ValueError("Caminho relativo inválido: " + text)
    return p


def regular(root, name):
    # /var e /tmp são aliases do sistema no macOS. Resolve a raiz confiada,
    # mas nunca um componente do caminho recebido do manifesto.
    root = root.resolve(strict=True)
    p = root.joinpath(*relative(name).parts)
    if any(q.is_symlink() for q in (p, *p.parents)) or not p.is_file():
        raise ValueError("Fonte irregular ou simbólico: " + str(p))
    return p


def cli(binary, *args, cwd):
    env = {k: v for k, v in os.environ.items() if not k.startswith(("LUA_", "SANTAFE_"))}
    p = subprocess.run([str(binary), *map(str, args)], cwd=cwd, env=env,
                       capture_output=True, text=True, timeout=45)
    if p.returncode:
        raise ValueError(p.stderr + p.stdout)


def build(source, binary, output, previous=None):
    source, binary = source.resolve(), binary.resolve()
    # Não reaproveitar nem apagar diretórios de saída existentes.
    if output.exists() or output.is_symlink():
        raise ValueError("Use uma pasta de saída nova: " + str(output))
    specification = json.loads(regular(source, "bibliotecas/catalogo.json").read_text())
    if set(specification) != {"formato", "pacotes"} or specification["formato"] != 1:
        raise ValueError("Curadoria incompatível")
    with tempfile.TemporaryDirectory(prefix="santafe-curadoria-") as work:
        work = Path(work)
        registry = work / "catalogo"
        registry.mkdir()
        if previous:
            # Valida novamente todos os envelopes pelo cliente, não apenas hashes.
            index = json.loads(regular(previous, "indice.json").read_text())
            if set(index) != {"formato", "pacotes"} or index["formato"] != 1:
                raise ValueError("Catálogo anterior incompatível")
            for name, versions in sorted(index["pacotes"].items()):
                for version, entry in sorted(versions.items()):
                    package = regular(previous, entry["arquivo"])
                    if digest(package) != entry["sha256"]:
                        raise ValueError("Pacote anterior adulterado")
                    data = json.loads(package.read_text())
                    if (data["manifesto"]["nome"], data["manifesto"]["versao"]) != (name, version):
                        raise ValueError("Identidade anterior divergente")
                    if data["manifesto"].get("dependencias", {}) != entry.get("dependencias", {}):
                        raise ValueError("Dependências anteriores divergentes")
                    cli(binary, "catalogo", registry, package, cwd=work)
        seen = set()
        for number, entry in enumerate(specification["pacotes"]):
            if set(entry) != {"manifesto", "fontes"}:
                raise ValueError("Curadoria com campos desconhecidos")
            manifest = dict(entry["manifesto"])
            identity = (manifest["nome"], manifest["versao"])
            if identity in seen:
                raise ValueError("Versão duplicada na curadoria")
            seen.add(identity)
            staging = work / ("fonte-" + str(number))
            staging.mkdir()
            for destination, origin in sorted(entry["fontes"].items()):
                src = regular(source, origin)
                dst = staging.joinpath(*relative(destination).parts)
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)
            manifest["arquivos"] = sorted(entry["fontes"])
            (staging / "santafe.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
            package = work / (str(number) + ".sfp")
            cli(binary, "empacote", staging, package, cwd=work)
            cli(binary, "catalogo", registry, package, cwd=work)
        index = json.loads((registry / "indice.json").read_text())
        rows = []
        hashes = {"indice.json": digest(registry / "indice.json")}
        for name, versions in sorted(index["pacotes"].items()):
            for version, entry in sorted(versions.items()):
                package = regular(registry, entry["arquivo"])
                manifest = json.loads(package.read_text())["manifesto"]
                hashes[entry["arquivo"]] = digest(package)
                esc = html.escape
                rows.append('<article><h2>' + esc(name) + ' <small>' + esc(version) + '</small></h2>'
                            '<p>' + esc(manifest["descricao"]) + '</p><pre><code>santafé instale '
                            + esc(name) + ' ' + esc(version) + '</code></pre><p>Licença: '
                            + esc(manifest["licenca"]) + ' · Autoria: ' + esc(', '.join(manifest["autores"]))
                            + '</p><p><a href="' + esc(entry["arquivo"], quote=True) + '">Pacote imutável</a>'
                            + ' · <a rel="noopener noreferrer" href="' + esc(manifest["fonte"], quote=True)
                            + '">Fonte</a></p><details><summary>SHA-256</summary><code>'
                            + entry["sha256"] + '</code></details></article>')
        page = '''<!doctype html><html lang="pt-BR"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Bibliotecas — Santafé</title><style>
:root{color-scheme:light dark}body{font:1rem/1.6 system-ui,sans-serif;max-width:64rem;margin:auto;padding:2rem}
a{color:#008577}article{border-top:1px solid #8886;padding:1.25rem 0}pre{padding:1rem;background:#8881;overflow:auto}
code{overflow-wrap:anywhere}small{font-size:.7em;font-weight:400}nav{display:flex;gap:1.5rem;flex-wrap:wrap}
</style><nav><a href="/">Santafé</a><a href="/baixar">Instalar a linguagem</a>
<a href="/est%C3%A1tico/manual/#bibliotecas-projeto">Manual</a><a href="indice.json">Catálogo JSON</a></nav>
<h1>Bibliotecas Santafé</h1><p>Catálogo curado, com versões imutáveis e licença explícita.
A instalação é local ao projeto; dependências e hashes ficam em <code>santafe.lock</code>.</p>
<p>Execute o comando dentro do projeto. Bibliotecas C exigem <code>--permitir-nativo</code> e um
compilador; não são uma área de execução isolada. Nenhum pacote recebe autorização automática para executar.</p>
''' + ''.join(rows) + '<footer><p>Contrato de catálogo 1 · <a href="SHA256SUMS">Hashes dos arquivos</a></p></footer></html>\n'
        (registry / "index.html").write_text(page, encoding="utf-8")
        hashes["index.html"] = digest(registry / "index.html")
        (registry / "SHA256SUMS").write_text(''.join(f'{value}  {key}\n' for key,value in sorted(hashes.items())))
        # Copia apenas arquivos públicos enumerados; exclui .santafe/trava.
        output.mkdir(parents=True, exist_ok=False)
        for name in [*hashes, "SHA256SUMS"]:
            dst = output / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(registry / name, dst)
    return index


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--fonte", type=Path, default=ROOT)
    p.add_argument("--binario", type=Path, default=ROOT / "src/santafé")
    p.add_argument("--saida", type=Path, required=True)
    p.add_argument("--anterior", type=Path)
    args = p.parse_args()
    build(args.fonte, args.binario, args.saida, args.anterior)
    print("Catálogo preparado, não publicado: " + str(args.saida))
