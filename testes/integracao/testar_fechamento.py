#!/usr/bin/env python3
"""Testa preparo e rollback sem privilégios, rede ou diretórios de produção."""
import importlib.util
import json
import os
from pathlib import Path
import pwd
import grp
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("fechamento", ROOT / "operação/fechamento-2.0.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def rejects(call):
    try:
        call()
    except ValueError:
        return
    raise AssertionError("alteração insegura aceita")


page = '''-- texto de outra página: 2.0.1
ap.rota("GET", "/baixar", função(req, res)
local html = [[<h5>Santafé 2.0.1</h5>
santafe-2.0.1.tar.gz santafe-2.0.1.zip
santafe-vscode-1.0.6.vsix Santafe.sublime-package?v=1.0.13]]
fim)
ap.rota("GET", "/outra", função(req, res)
-- manter 2.0.1
fim)
'''
converted = m.download_page(page)
assert m.download_page(converted) == converted
assert converted.startswith('-- texto de outra página: 2.0.1')
assert converted.endswith('-- manter 2.0.1\nfim)\n')
rejects(lambda: m.download_page(page.replace("1.0.6.vsix", "1.0.5.vsix")))
cache = '''<a href="/estático/wasm/">Experimente</a>
return "/estático/wasm/" + path + "?v=anterior";
<script src="/estático/wasm/santafe.js?v=anterior"></script>
<script src="santafe.js?v=4"></script>'''
changed = m.cache_wasm(cache)
assert changed.count(m.BASE_WASM) == 3
assert '<a href="/estático/wasm/">' in changed
assert m.cache_wasm(changed) == changed

with tempfile.TemporaryDirectory(prefix="santafe-fechamento-teste-") as temporary:
    root = Path(temporary).resolve()
    source, snapshot, prefix, downloads, system, site, public, out = [root / name for name in
        ("source", "snapshot", "prefix", "downloads", "system", "site", "public", "out")]
    for directory in (source, snapshot, prefix, downloads, system, site, public, out):
        directory.mkdir()
    def write(path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data)
    app = root / "app.fé"
    write(app, page)
    write(site / "sfdev.fé", page)
    os.environ["SANTAFE_FECHAMENTO_APP"] = str(app)
    for rel in ("src/santafe.js", "src/santafe.wasm", "docs/manual.html", "docs/validar-manual.py"):
        write(source / rel, cache if rel.endswith("html") else "fixture")
    write(snapshot / "README.md", "Fonte público")
    (source / "operação").mkdir()
    shutil.copyfile(ROOT / "operação/preparar-editores-portal.py", source / "operação/preparar-editores-portal.py")
    for rel in ("bin/santafé", "bin/santafec", "bin/santafé-sls", "lib/liblua.a",
                "lib/pkgconfig/santafe.pc", "share/santafé/1.0/ferramentas/sls.fé",
                *["include/" + n for n in ("lua.h", "luaconf.h", "lauxlib.h", "lualib.h", "lua.hpp")]):
        write(prefix / rel, "fixture")
    write(public / "baixar/SHA256SUMS", "0" * 64 + "  santafe-2.0.1.tar.gz\n")
    write(public / "wasm/index.html", cache)
    for ext in ("tar.gz", "zip"):
        write(downloads / f"santafe-2.0.2.{ext}", "fixture")
    m.prepare(source, snapshot, prefix, downloads, system, site, public, out)
    assert app.read_text() == page
    assert not (system / "bin/santafé").exists()
    assert 'santafe-2.0.1.tar.gz' in (out / "SHA256SUMS").read_text()
    plan = out / "plan.json"
    entries = json.loads(plan.read_text())
    user = pwd.getpwuid(os.getuid()).pw_name
    group = grp.getgrgid(os.getgid()).gr_name
    for e in entries:
        e["owner"] = user + ":" + group
    plan.write_text(json.dumps(entries))
    backup = root / "backup"
    m.install(plan, backup)
    m.verify(plan)
    m.rollback(backup)
    assert app.read_text() == page
    assert not (system / "bin/santafé").exists()
    # Falha no meio: todos os alvos tocados devem voltar ao estado original.
    original_copy = m.atomic_copy
    calls = [0]
    def interrupted(*args):
        calls[0] += 1
        if calls[0] == 3:
            raise OSError("falha simulada")
        original_copy(*args)
    m.atomic_copy = interrupted
    try:
        m.install(plan, root / "partial")
        raise AssertionError("falha não exercitada")
    except OSError:
        pass
    finally:
        m.atomic_copy = original_copy
    m.rollback(root / "partial")
    assert app.read_text() == page
    assert not (system / "bin/santafé").exists()
    app.write_text(page + "-- concorrente")
    rejects(lambda: m.install(plan, root / "concurrent"))
    assert app.read_text().endswith("-- concorrente")
    app.write_text(page)
    write(public / "baixar/santafe-2.0.2.tar.gz", "conteúdo diferente")
    rejects(lambda: m.prepare(source, snapshot, prefix, downloads, system, site, public, out))
    link = root / "link"
    link.symlink_to(app)
    rejects(lambda: m.safe_destination(link))
print("Fechamento: preparo, cache, imutabilidade, concorrência, instalação e rollback parcial: ok")
