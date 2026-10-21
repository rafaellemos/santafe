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


page = '''-- texto de outra página: 2.0.2
ap.rota("GET", "/baixar", função(req, res)
local html = [[<h5>Santafé 2.0.2</h5>
santafe-2.0.2.tar.gz santafe-2.0.2.zip
santafe-vscode-1.0.6.vsix Santafe.sublime-package?v=1.0.13]]
fim)
ap.rota("GET", "/outra", função(req, res)
-- manter 2.0.2
fim)
'''
converted = m.download_page(page)
assert m.download_page(converted) == converted
assert converted.startswith('-- texto de outra página: 2.0.2')
assert converted.endswith('-- manter 2.0.2\nfim)\n')
assert f'santafe-{m.VERSION}.tar.gz' in converted
rejects(lambda: m.download_page(page.replace("1.0.6.vsix", "1.0.5.vsix")))
rejects(lambda: m.download_page(page.replace('Santafé 2.0.2</h5>', 'Santafé 9.0.0</h5>')))
cache = '''<a href="/estático/wasm/">Experimente</a>
return "/estático/wasm/" + path + "?v=anterior";
<script src="/estático/wasm/santafe.js?v=anterior"></script>
<script src="santafe.js?v=4"></script>'''
changed = m.cache_wasm(cache)
assert changed.count(m.BASE_WASM) == 3
assert '<a href="/estático/wasm/">' in changed
assert m.cache_wasm(changed) == changed
assert m.cache_wasm(cache.replace('/estático/wasm/', '/estático/wasm/2.0.2/')).count(m.BASE_WASM) == 3

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
                "share/santafé/1.0/bibf/rpdf_unicode.fé", "share/santafé/1.0/bibf/rpdf/LEIA-ME.md",
                *["include/" + n for n in ("lua.h", "luaconf.h", "lauxlib.h", "lualib.h", "lua.hpp")]):
        write(prefix / rel, "fixture")
    write(prefix / 'lib/pkgconfig/santafe.pc', f'prefix={prefix}\nVersion: {m.VERSION}\n')
    write(public / "baixar/SHA256SUMS", "0" * 64 + "  santafe-2.0.2.tar.gz\n")
    old_download = public / 'baixar/santafe-2.0.2.tar.gz'
    old_wasm = public / 'wasm/2.0.2/santafe.wasm'
    for old in (old_download, old_wasm):
        write(old, 'histórico imutável')
    rpdf = system / 'share/santafé/1.0/bibf/rpdf_unicode.fé'
    write(rpdf, 'biblioteca anterior')
    write(public / "wasm/index.html", cache)
    for ext in ("tar.gz", "zip"):
        write(downloads / f"santafe-{m.VERSION}.{ext}", "fixture")
    m.prepare(source, snapshot, prefix, downloads, system, site, public, out)
    assert app.read_text() == page
    assert not (system / "bin/santafé").exists()
    assert 'santafe-2.0.2.tar.gz' in (out / "SHA256SUMS").read_text()
    manifest = json.loads((out / 'release.json').read_text())
    assert manifest['version'] == m.VERSION
    assert manifest['source_tag'] is None
    assert manifest['intended_source_tag'] == 'v' + m.VERSION
    assert (out / 'santafe.pc').read_text().splitlines()[0] == f'prefix={system}'
    plan = out / "plan.json"
    entries = json.loads(plan.read_text())
    libraries = [e['target'] for e in entries if '/share/santafé/1.0/bibf/' in e['target']]
    assert set(libraries) == {str(rpdf), str(rpdf.parent / 'rpdf/LEIA-ME.md')}
    user = pwd.getpwuid(os.getuid()).pw_name
    group = grp.getgrgid(os.getgid()).gr_name
    for e in entries:
        e["owner"] = user + ":" + group
    plan.write_text(json.dumps(entries))
    backup = root / "backup"
    m.install(plan, backup)
    m.verify(plan)
    assert (system / 'lib/pkgconfig/santafe.pc').read_text().splitlines()[0] == f'prefix={system}'
    assert rpdf.read_text() == 'fixture'
    for old in (old_download, old_wasm):
        assert old.read_text() == 'histórico imutável'
    m.rollback(backup)
    assert rpdf.read_text() == 'biblioteca anterior'
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
    write(public / f"baixar/santafe-{m.VERSION}.tar.gz", "conteúdo diferente")
    rejects(lambda: m.prepare(source, snapshot, prefix, downloads, system, site, public, out))
    link = root / "link"
    link.symlink_to(app)
    rejects(lambda: m.safe_destination(link))
print("Fechamento: preparo, cache, imutabilidade, concorrência, instalação e rollback parcial: ok")
