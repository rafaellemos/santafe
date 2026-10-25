#!/usr/bin/env python3
"""Extrai somente a base selada e aplica uma correção MinGW isolada."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import tarfile

SOURCE_SHA = '9705b3a4599f4a884cd2ac2118f436a00ed106abe752740c346574abf8b5ed54'
OLD = '''mingw:
	$(MAKE) "LUA_A=libsantafe.a" "LUA_T=santafe.exe" \\
	"AR=$(AR) rcu" "RANLIB=$(RANLIB)" \\
	"SYSCFLAGS=-DLUA_USE_WINDOWS" "SYSLIBS=-lws2_32" "SYSLDFLAGS=-static" santafe.exe
	$(MAKE) "LUAC_T=santafec.exe" santafec.exe
'''
NEW = '''# Interpretador e compilador usam a mesma biblioteca, opções e IBA.
# AR já contém suas opções; não acrescentar outro "rcu".
WINDRES ?= windres
santafe-windows.o: santafe.rc santafe.manifest
	$(WINDRES) -i santafe.rc -o $@

mingw: santafe-windows.o
	$(MAKE) "LUA_A=libsantafe.a" "LUA_T=santafe.exe" "LUAC_T=santafec.exe" \\
	"AR=$(AR)" "RANLIB=$(RANLIB)" \\
	"SYSCFLAGS=-DLUA_USE_WINDOWS" "SYSLIBS=-lws2_32" "SYSLDFLAGS=-static" \\
	"MYLDFLAGS=$(MYLDFLAGS) santafe-windows.o" all
'''

def prepare(archive, destination):
    if destination.exists():
        raise ValueError('destino já existe')
    if hashlib.sha256(archive.read_bytes()).hexdigest() != SOURCE_SHA:
        raise ValueError('fontes divergentes da entrega selada')
    with tarfile.open(archive) as pack:
        names = set()
        for entry in pack.getmembers():
            name = PurePosixPath(entry.name)
            if (not entry.isfile() or name.is_absolute() or '..' in name.parts
                    or '\\' in entry.name or ':' in entry.name or entry.name in names):
                raise ValueError('entrada insegura no arquivo')
            names.add(entry.name)
        destination.mkdir(parents=True)
        # Escrever manualmente: não materializa links, dispositivos ou metadados.
        for entry in pack.getmembers():
            path = destination / entry.name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(pack.extractfile(entry).read())
    manifest = json.loads((destination/'MANIFESTO-FONTES.json').read_text(encoding='utf-8'))
    for name, expected in manifest.items():
        if hashlib.sha256((destination/name).read_bytes()).hexdigest() != expected:
            raise ValueError('arquivo divergente: '+name)
    makefile = destination/'src/Makefile'
    before = makefile.read_bytes()
    text = before.decode('utf-8')
    if text.count(OLD) != 1:
        raise ValueError('receita MinGW inesperada')
    after = text.replace(OLD, NEW).encode('utf-8')
    makefile.write_bytes(after)
    additions={}
    for name in ('santafe.rc','santafe.manifest'):
        data=(Path(__file__).parent/name).read_bytes()
        (destination/'src'/name).write_bytes(data)
        additions['src/'+name]=hashlib.sha256(data).hexdigest()
    evidence = {'fonte_sha256': SOURCE_SHA, 'arquivos_conferidos':len(manifest),
                'alterado':'src/Makefile', 'antes':hashlib.sha256(before).hexdigest(),
                'depois':hashlib.sha256(after).hexdigest(), 'adicionados':additions,
                'producao_alterada':False}
    (destination/'PREPARACAO-WINDOWS.json').write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf-8')
    return evidence

if __name__ == '__main__':
    print(json.dumps(prepare(Path(sys.argv[1]), Path(sys.argv[2])), indent=2))
