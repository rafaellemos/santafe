#!/usr/bin/env python3
"""Prepara fonte24 com IBA3 padrão; nunca reaplica as sobreposições C antigas."""
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import sys
import tarfile

BASE = 'de81368853e333a004e5eaab49bc262e934ca06a987fe9fd039d46429bc6e5db'


def prepare(archive, destination, windows):
    if destination.exists() or destination.is_symlink():
        raise ValueError('destino precisa ser novo')
    if hashlib.sha256(archive.read_bytes()).hexdigest() != BASE:
        raise ValueError('fonte24 divergente')
    rows = {}
    with tarfile.open(archive) as package:
        for item in package:
            name = PurePosixPath(item.name)
            if (not item.isfile() or name.is_absolute() or '..' in name.parts
                    or str(name) != item.name or item.name in rows
                    or '\\' in item.name or ':' in item.name
                    or item.size > 32 * 1024**2):
                raise ValueError('entrada insegura')
            rows[item.name] = (package.extractfile(item).read(), item.mode & 0o755)
    manifest = json.loads(rows['MANIFESTO-FONTES.json'][0])
    actual = {n: hashlib.sha256(b).hexdigest() for n, (b, _) in rows.items()
              if n != 'MANIFESTO-FONTES.json'}
    if manifest != actual or len(manifest) != 908:
        raise ValueError('manifesto24 divergente')
    spec = importlib.util.spec_from_file_location('mingw_receita', windows/'preparar.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    before = rows['src/Makefile'][0]
    text = before.decode('utf-8')
    if text.count(module.NEW) == 1:
        pass  # A fonte24 já incorporou esta receita; conferir sem reescrever.
    elif text.count(module.OLD) == 1:
        rows['src/Makefile'] = (text.replace(module.OLD, module.NEW).encode(), rows['src/Makefile'][1])
    else:
        raise ValueError('receita MinGW inesperada')
    for name in ('santafe.rc', 'santafe.manifest'):
        if 'src/'+name in rows and rows['src/'+name][0] != (windows/name).read_bytes():
            raise ValueError('recurso Windows mudou: '+name)
        rows['src/'+name] = ((windows/name).read_bytes(), 0o644)
    destination.mkdir(parents=True, mode=0o700)
    for name, (data, mode) in rows.items():
        p = destination/name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        p.chmod(mode)
    evidence = {'candidato': 'dados.25', 'fonte24_sha256': BASE,
                'arquivos_base': len(manifest), 'nucleo_c_h_inalterado': True,
                'contrato_padrao': 'IBA3', 'producao_alterada': False,
                'makefile_sha256': hashlib.sha256(rows['src/Makefile'][0]).hexdigest(),
                'recursos': {n: hashlib.sha256(rows['src/'+n][0]).hexdigest()
                             for n in ('santafe.rc', 'santafe.manifest')}}
    (destination/'PREPARACAO-WINDOWS.json').write_text(json.dumps(evidence, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    prepare(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
