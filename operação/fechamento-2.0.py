#!/usr/bin/env python3
"""Plano e transação reversível do fechamento 2.0.2; sem executar aplicações."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile
import pwd
import grp

VERSION = "2.0.2"
BASE_WASM = "/estático/wasm/2.0.2/"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def cache_wasm(text):
    # Somente URLs do executor, nunca os links para a página do playground.
    text = re.sub(r'/estático/wasm/(?:2\.0\.2/)?(?=santafe\.(?:js|wasm)|["\']\s*\+\s*path\b)',
                  BASE_WASM, text)
    return re.sub(r'(?<=src=")santafe\.js(?:\?v=[^"<>]*)?', BASE_WASM + "santafe.js", text)


def download_page(text):
    marker = 'ap.rota("GET", "/baixar", função(req, res)'
    if text.count(marker) != 1:
        raise ValueError("Rota /baixar ausente ou duplicada")
    start = text.index(marker)
    following = re.search(r'(?m)^ap\.rota\(', text[start + len(marker):])
    if following is None:
        raise ValueError("Fim da rota /baixar não encontrado")
    end = start + len(marker) + following.start()
    part = text[start:end]
    if not all(s in part for s in ('santafe-vscode-1.0.6.vsix', 'Santafe.sublime-package?v=1.0.13')):
        raise ValueError("Publique primeiro os editores já homologados")
    if 'Santafé 2.0.1</h5>' not in part and 'Santafé 2.0.2</h5>' not in part:
        raise ValueError("Versão inesperada na página; não substituir cegamente")
    part = part.replace("2.0.1", VERSION)
    for ext in ("tar.gz", "zip"):
        if f'santafe-{VERSION}.{ext}' not in part:
            raise ValueError("Download esperado ausente: " + ext)
    return text[:start] + part + text[end:]


def safe_destination(path):
    for item in (path, *path.parents):
        if item.is_symlink():
            raise ValueError("Destino contém link simbólico: " + str(item))
    if path.exists() and not path.is_file():
        raise ValueError("Destino não é arquivo regular: " + str(path))


def prepare(source, snapshot, prefix, downloads, system, site, public, out, owner="rafael"):
    """system=/usr/local; site=/home/rafael/santafe-fonte/site-sfdev."""
    out.mkdir(parents=True, exist_ok=True)
    app = Path(os.environ.get("SANTAFE_FECHAMENTO_APP", "/opt/sfdev.fé"))
    if app.read_bytes() != (site / "sfdev.fé").read_bytes():
        raise ValueError("Portal instalado difere do fonte: preserve a edição local")
    entries = []

    def add(src, dst, who, mode=0o644, immutable=False):
        safe_destination(dst)
        if not src.is_file() or src.is_symlink():
            raise ValueError("Origem inválida: " + str(src))
        if immutable and dst.exists() and sha(src) != sha(dst):
            raise ValueError("Versão imutável já existe com conteúdo diferente: " + str(dst))
        old = dst.stat() if dst.exists() else None
        entries.append(dict(source=str(src), target=str(dst), sha256=sha(src),
                            before=sha(dst) if old else None, mode=mode, owner=who,
                            old_mode=stat.S_IMODE(old.st_mode) if old else None,
                            old_uid=old.st_uid if old else None, old_gid=old.st_gid if old else None))

    page = out / "sfdev.fé"
    page.write_text(cache_wasm(download_page(app.read_text())), encoding="utf-8")
    add(page, app, "sfdev:sfdev", 0o755)
    add(page, site / "sfdev.fé", f"{owner}:{owner}")
    manual = out / "manual.html"
    manual.write_text(cache_wasm((source / "docs/manual.html").read_text()), encoding="utf-8")
    add(manual, public / "manual/index.html", "www-data:www-data")
    add(manual, site / "manual.html", f"{owner}:{owner}")
    add(source / "docs/validar-manual.py", site / "validar-manual.py", f"{owner}:{owner}")
    # Mantém os endereços históricos do executor intactos para abas em cache.
    for rel in ("wasm/index.html", "wasm/IDE/index.html"):
        target = public / rel
        if not target.is_file():
            continue
        modified = cache_wasm(target.read_text())
        if modified != target.read_text():
            new = out / (rel.replace("/", "-") + ".html")
            new.write_text(modified)
            add(new, target, "www-data:www-data")
            if rel == "wasm/index.html":
                add(new, site / "wasm-index.html", f"{owner}:{owner}")
    for name in ("santafe.js", "santafe.wasm"):
        add(source / "src" / name, public / "wasm" / VERSION / name,
            "www-data:www-data", immutable=True)
    for name in ("santafé", "santafec", "santafé-sls"):
        add(prefix / "bin" / name, system / "bin" / name, "root:root", 0o755)
    for name in ("lua.h", "luaconf.h", "lauxlib.h", "lualib.h", "lua.hpp"):
        add(prefix / "include" / name, system / "include" / name, "root:root")
    for rel in ("lib/liblua.a", "lib/pkgconfig/santafe.pc", "share/santafé/1.0/ferramentas/sls.fé"):
        add(prefix / rel, system / rel, "root:root")
    spec = importlib.util.spec_from_file_location("editor_publish", source / "operação/preparar-editores-portal.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    hashes = {}
    for ext in ("tar.gz", "zip"):
        name = f"santafe-{VERSION}.{ext}"
        hashes[name] = sha(downloads / name)
        add(downloads / name, public / "baixar" / name, "www-data:www-data", immutable=True)
        add(downloads / name, site / "baixar" / name, f"{owner}:{owner}", immutable=True)
    sums = out / "SHA256SUMS"
    sums.write_text(module.atualize_somas((public / "baixar/SHA256SUMS").read_text(), hashes))
    add(sums, public / "baixar/SHA256SUMS", "www-data:www-data")
    add(sums, site / "baixar/SHA256SUMS", f"{owner}:{owner}")
    # Fonte exato extraído do TAR, sem sobrepor a árvore operacional antiga.
    for file in sorted(snapshot.rglob("*")):
        if file.is_file():
            add(file, site.parent / "versoes" / VERSION / file.relative_to(snapshot),
                f"{owner}:{owner}", stat.S_IMODE(file.stat().st_mode), immutable=True)
    manifest = out / "release.json"
    manifest.write_text(json.dumps(dict(version=VERSION, publication_revision=2,
        source_tag="v2.0.2-r2", sls="0.1.1", vscode="1.0.6", sublime="1.0.13",
        downloads=hashes, source=str(site.parent / "versoes" / VERSION),
        wasm_url=BASE_WASM, restarted_services=["sfdev.service"],
        persistent_services_not_restarted=True), ensure_ascii=False, indent=2) + "\n")
    add(manifest, public / "baixar/santafe-2.0.2.json", "www-data:www-data", immutable=True)
    add(manifest, site.parent / "VERSAO-PUBLICADA.json", f"{owner}:{owner}")
    targets = [e["target"] for e in entries]
    if len(set(targets)) != len(targets):
        raise ValueError("Plano com destinos duplicados")
    (out / "plan.json").write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n")
    print(f"Plano preparado: {len(entries)} arquivos; nenhum instalado")


def atomic_copy(src, dst, mode, uid, gid):
    dst = Path(dst)
    safe_destination(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".santafe-", dir=dst.parent)
    try:
        with os.fdopen(fd, "wb") as stream, Path(src).open("rb") as incoming:
            shutil.copyfileobj(incoming, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(tmp, mode)
        if os.geteuid() == 0:
            os.chown(tmp, uid, gid)
        os.replace(tmp, dst)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def install(plan, backup):
    entries = json.loads(plan.read_text())
    # Verificação integral antes da primeira troca; detecta alterações concorrentes.
    for e in entries:
        dst = Path(e["target"])
        safe_destination(dst)
        if (sha(dst) if dst.exists() else None) != e["before"] or sha(e["source"]) != e["sha256"]:
            raise ValueError("Arquivo mudou após o preparo: " + str(dst))
        user, group = e["owner"].split(":")
        e["uid"], e["gid"] = pwd.getpwnam(user).pw_uid, grp.getgrnam(group).gr_gid
    backup.mkdir(mode=0o700, parents=True, exist_ok=False)
    # Backup de TODOS os alvos antes de qualquer escrita operacional.
    for i, e in enumerate(entries):
        if e["before"] is not None:
            shutil.copyfile(e["target"], backup / f"{i:05d}.before")
    (backup / "plan.json").write_text(json.dumps(entries, ensure_ascii=False, indent=2))
    (backup / "touched.json").write_text("[]")
    touched = []
    for i, e in enumerate(entries):
        if e["before"] == e["sha256"]:
            continue
        touched.append(i)
        (backup / "touched.json").write_text(json.dumps(touched))
        atomic_copy(e["source"], e["target"], e["mode"], e["uid"], e["gid"])
    verify(plan)


def verify(plan):
    for e in json.loads(plan.read_text()):
        if sha(e["target"]) != e["sha256"]:
            raise ValueError("Validação instalada falhou: " + e["target"])
    print("Todos os arquivos instalados correspondem ao plano")


def rollback(backup):
    entries = json.loads((backup / "plan.json").read_text())
    touched = json.loads((backup / "touched.json").read_text())
    for i in reversed(touched):
        e = entries[i]
        if e["before"] is None:
            Path(e["target"]).unlink(missing_ok=True)
        else:
            atomic_copy(backup / f"{i:05d}.before", e["target"], e["old_mode"], e["old_uid"], e["old_gid"])
    for i in touched:
        e = entries[i]
        target = Path(e["target"])
        if (sha(target) if target.exists() else None) != e["before"]:
            raise ValueError("Restauração incompleta: " + str(target))
    print("Arquivos anteriores restaurados; cópia recuperável: " + str(backup))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "install", "verify", "rollback"))
    for arg in ("source", "snapshot", "prefix", "downloads", "system", "site", "public", "out", "plan", "backup"):
        parser.add_argument("--" + arg, type=Path)
    args = parser.parse_args()
    if args.action == "prepare":
        prepare(args.source, args.snapshot, args.prefix, args.downloads, args.system,
                args.site, args.public, args.out)
    elif args.action == "install":
        install(args.plan, args.backup)
    elif args.action == "verify":
        verify(args.plan)
    else:
        rollback(args.backup)
