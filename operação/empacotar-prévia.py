#!/usr/bin/env python3
"""Gera uma distribuição pública a partir da árvore de trabalho.

`git archive` só inclui arquivos já versionados. Enquanto a próxima versão ainda
está em desenvolvimento, bibliotecas, ferramentas e testes novos podem ainda
não estar em um commit; por isso esta ferramenta cria uma cópia explícita e
filtrada da árvore atual, sem binários, segredos ou resultados de compilação.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import os
from pathlib import Path
import shutil
import stat
import tarfile
import tempfile
import unicodedata
import zipfile


RAIZ = Path(__file__).resolve().parents[1]
SAIDA = RAIZ / "dist"
DIRETORIOS_IGNORADOS = {".git", "dist", "publicar", "__pycache__", ".pytest_cache"}
SUFIXOS_IGNORADOS = {
    ".o", ".a", ".so", ".dylib", ".dll", ".exe", ".res", ".zip", ".tar.gz",
    ".deb", ".pdf", ".pyc", ".wasm",
}
CAMINHOS_IGNORADOS = {
    Path("src/santafé"),
    Path("src/santafé-sls"),
    Path("src/santafe"),
    Path("src/santafec"),
    Path("src/santafe.js"),
    Path("src/santafe.worker.js"),
    Path("src/santafe.data"),
}
RECURSOS_DISTRIBUIDOS = {
    Path("extensões/vscode/vendor/vscode-oniguruma/release/onig.wasm"),
}
EXIGIDOS = {
    Path("Makefile"),
    Path("README.md"),
    Path("ferramentas/sls/sls.fé"),
    Path("ferramentas/sls/santafé-sls"),
    Path("extensões/vscode/package.json"),
    Path("extensões/vscode/extension.js"),
    Path("extensões/sublime/Santafe.py"),
    Path("extensões/sublime/Santafe.sublime-syntax"),
    *RECURSOS_DISTRIBUIDOS,
}
DATA_FIXA = 1792195200  # 2026-10-17T00:00:00Z; permite artefatos repetíveis.


def ignorado(relativo: Path) -> bool:
    if relativo in RECURSOS_DISTRIBUIDOS:
        return False  # runtime licenciado do editor, não executável do núcleo
    if relativo.parts[:2] == ("docs", "evidencias"):
        return True  # capturas/relatórios locais não pertencem ao pacote público
    if relativo in {Path('testes/recursos/tls-local-certificado.pem'),
                    Path('testes/recursos/tls-local-chave.pem')}:
        return False  # certificados públicos de teste; nunca usar em produção
    if relativo in CAMINHOS_IGNORADOS:
        return True
    if any(parte in DIRETORIOS_IGNORADOS for parte in relativo.parts):
        return True
    nome = relativo.name
    if nome == ".DS_Store" or nome.endswith((".swp", ".swo", "~", ".pulso", ".pem", ".key")):
        return True
    if (nome.endswith(".env") or nome.startswith(".env")) and not nome.endswith(".env.exemplo"):
        return True
    if nome.endswith(("_rsa", "_ed25519")):
        return True
    return any(nome.endswith(sufixo) for sufixo in SUFIXOS_IGNORADOS)


def copie_arvore(destino: Path) -> None:
    for diretorio, subdiretorios, arquivos in os.walk(RAIZ):
        caminho = Path(diretorio)
        relativo = caminho.relative_to(RAIZ)
        subdiretorios[:] = [
            nome for nome in subdiretorios if not ignorado(relativo / nome)
        ]
        if relativo != Path(".") and ignorado(relativo):
            continue
        (destino / relativo).mkdir(parents=True, exist_ok=True)
        for nome in sorted(arquivos):
            origem = caminho / nome
            rel_arquivo = origem.relative_to(RAIZ)
            if ignorado(rel_arquivo) or origem.is_symlink():
                continue
            alvo = destino / rel_arquivo
            alvo.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(origem, alvo)


def informações_fixadas(info: tarfile.TarInfo) -> tarfile.TarInfo:
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    info.mtime = DATA_FIXA
    return info


def escreva_tar(raiz: Path, destino: Path, prefixo: str) -> None:
    with destino.open("wb") as bruto:
        with gzip.GzipFile(filename="", mode="wb", fileobj=bruto, mtime=0) as compactado:
            with tarfile.open(fileobj=compactado, mode="w") as arquivo:
                for caminho in sorted(raiz.rglob("*")):
                    relativo = caminho.relative_to(raiz)
                    arquivo.add(caminho, arcname=unicodedata.normalize('NFC', f"{prefixo}/{relativo.as_posix()}"),
                                filter=informações_fixadas, recursive=False)


def escreva_zip(raiz: Path, destino: Path, prefixo: str) -> None:
    with zipfile.ZipFile(destino, "w", compression=zipfile.ZIP_DEFLATED) as arquivo:
        for caminho in sorted(raiz.rglob("*")):
            if caminho.is_dir():
                continue
            relativo = caminho.relative_to(raiz).as_posix()
            info = zipfile.ZipInfo(unicodedata.normalize('NFC', f"{prefixo}/{relativo}"), date_time=(2026, 10, 17, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (stat.S_IMODE(caminho.stat().st_mode) | stat.S_IFREG) << 16
            arquivo.writestr(info, caminho.read_bytes())


def soma(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def principal() -> None:
    argumentos = argparse.ArgumentParser()
    argumentos.add_argument("--versão", required=True)
    versão = argumentos.parse_args().versão
    prefixo = f"santafe-{versão}"

    with tempfile.TemporaryDirectory(prefix="santafe-distribuição-") as temporário:
        raiz_da_distribuição = Path(temporário) / prefixo
        copie_arvore(raiz_da_distribuição)
        ausentes = sorted(str(item) for item in EXIGIDOS if not (raiz_da_distribuição / item).is_file())
        if ausentes:
            raise SystemExit("arquivos obrigatórios ausentes: " + ", ".join(ausentes))

        SAIDA.mkdir(exist_ok=True)
        tar = SAIDA / f"{prefixo}.tar.gz"
        zip_ = SAIDA / f"{prefixo}.zip"
        escreva_tar(raiz_da_distribuição, tar, prefixo)
        escreva_zip(raiz_da_distribuição, zip_, prefixo)
        (SAIDA / "SHA256SUMS").write_text(
            f"{soma(tar)}  {tar.name}\n{soma(zip_)}  {zip_.name}\n", encoding="utf-8"
        )
        print(tar)
        print(zip_)
        print(SAIDA / "SHA256SUMS")


if __name__ == "__main__":
    principal()
