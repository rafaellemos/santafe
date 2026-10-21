#!/usr/bin/env python3
"""Catálogo real, determinismo, retenção de versões e instalação sem produção."""
import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("catalogo", ROOT / "operação/preparar-catalogo-bibliotecas.py")
catalogo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalogo)
SF = ROOT / "src/santafé"


def files(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}


def refused(fn):
    try:
        fn()
    except (ValueError, OSError):
        return
    raise AssertionError('entrada insegura aceita')


with tempfile.TemporaryDirectory(prefix="santafe-catalogo-") as temporary:
    work = Path(temporary)
    a, b, c = (work / name for name in ('a', 'b', 'c'))
    index = catalogo.build(ROOT, SF, a)
    catalogo.build(ROOT, SF, b)
    assert files(a) == files(b), 'catálogo não determinístico'
    catalogo.build(ROOT, SF, c, previous=a)
    assert files(c) == files(a), 'republicação alterou conteúdo imutável'
    assert set(index['pacotes']) == {'semver'}
    for name in files(a):
        assert not any(p.startswith('.') for p in Path(name).parts)
    for line in (a / 'SHA256SUMS').read_text().splitlines():
        digest, name = line.split('  ', 1)
        assert hashlib.sha256((a / name).read_bytes()).hexdigest() == digest
    project = work / 'projeto'; project.mkdir()
    env = {k:v for k,v in os.environ.items() if not k.startswith(('LUA_', 'SANTAFE_'))}
    def run(*args):
        p = subprocess.run([str(SF), *map(str,args)], cwd=project, env=env, capture_output=True, text=True, timeout=30)
        assert p.returncode == 0, p.stderr + p.stdout
    run('instale', 'semver', '^1.0.0', '--repositorio-local', a)
    run('-e', 'local V=importe "semver"; garanta(V.compare("1.2.0","1.1.9")==1); garanta(V.satisfaz("1.2.3","^1.0.0")); garanta(não V.satisfaz("2.0.0","^1.0.0")); garanta(não proteja(V.compare,"errado","1.0.0"))')
    run('instale', '--travado', '--sem-rede', '--repositorio-local', a)
    refused(lambda: catalogo.build(ROOT, SF, a))
    entry = index['pacotes']['semver']['1.0.0']
    (a / entry['arquivo']).write_text('alterado')
    refused(lambda: catalogo.build(ROOT, SF, work/'bad', previous=a))
    assert not (work/'bad').exists()
    (work/'link').symlink_to(ROOT, target_is_directory=True)
    refused(lambda: catalogo.regular(work, 'link/LICENSE'))
    print('Catálogo oficial: biblioteca real, determinismo, hashes, imutabilidade, confinamento e instalação: ok')
