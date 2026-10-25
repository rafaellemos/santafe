"""Preserve notices from the exact compiled sources in both Windows packages."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import re
import subprocess
import zipfile

DIRECTORY = 'LICENCAS-INCORPORADAS'
SOURCES = (
    ('src/lua.h', 'Lua-MIT.txt', 'Lua 5.3.6 modificado', 'MIT', b'Lua.org, PUC-Rio', b'Permission is hereby granted'),
    ('src/lua_cjson.c', 'lua-cjson-MIT.txt', 'Lua CJSON modificado', 'MIT', b'Mark Pulford', b'Permission is hereby granted'),
    ('src/strbuf.c', 'strbuf-MIT.txt', 'strbuf', 'MIT', b'Mark Pulford', b'Permission is hereby granted'),
    ('src/fpconv.c', 'fpconv-MIT.txt', 'fpconv modificado', 'MIT', b'Mark Pulford', b'Permission is hereby granted'),
    ('src/zlib.h', 'zlib-1.3.1-LICENSE.txt', 'zlib 1.3.1', 'Zlib', b'1995-2024 Jean-loup Gailly', b'This notice may not be removed'),
    ('ferramentas/unicode/17.0.0/LICENSE.txt', 'Unicode-LICENSE.txt', 'Unicode UCD 17.0.0', 'Unicode-3.0', b'Unicode', b'Permission is hereby granted'),
)

def digest(data):
    return hashlib.sha256(data).hexdigest()

def extract_notice(source, data, owner, permission):
    parts = [data] if source.endswith('LICENSE.txt') else re.findall(rb'/\*.*?\*/', data, re.S)
    matches = [part for part in parts if owner in part and permission in part]
    if len(matches) != 1:
        raise ValueError('Aviso ausente ou ambíguo no fonte: ' + source)
    return matches[0] if source.endswith('LICENSE.txt') else matches[0] + b'\n'

def prepare(root, destination):
    target = destination / DIRECTORY
    target.mkdir()
    entries = []
    for source, name, component, license_id, owner, permission in SOURCES:
        path = root / source
        if path.is_symlink():
            raise ValueError('Vínculo recusado no fonte: ' + source)
        data = path.read_bytes()
        notice = extract_notice(source, data, owner, permission)
        (target / name).write_bytes(notice)
        entries.append(dict(fonte=source, fonte_sha256=digest(data), arquivo=name,
                            sha256=digest(notice), componente=component, licenca=license_id))
    (target / 'INDICE.json').write_text(json.dumps(entries, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    verify_tree(destination)
    return entries

def verify(read):
    entries = json.loads(read(DIRECTORY + '/INDICE.json').decode('utf-8'))
    expected = {s[1]: s for s in SOURCES}
    names = [e['arquivo'] for e in entries]
    if len(names) != len(set(names)) or set(names) != set(expected):
        raise ValueError('Inventário de avisos incompleto ou duplicado')
    for entry in entries:
        source, name, component, license_id, owner, permission = expected[entry['arquivo']]
        data = read(DIRECTORY + '/' + name)
        if (digest(data) != entry['sha256'] or owner not in data or permission not in data
                or entry['fonte'] != source or entry['licenca'] != license_id
                or not re.fullmatch(r'[0-9a-f]{64}', entry['fonte_sha256'])):
            raise ValueError('Aviso inválido: ' + name)
    return len(entries)

def verify_tree(root):
    def read(name):
        path = root / name
        if path.is_symlink():
            raise ValueError('Vínculo recusado no aviso: ' + name)
        return path.read_bytes()
    return verify(read)

def verify_archive(path):
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        if len(names) != len(set(names)):
            raise ValueError('Entradas ZIP duplicadas')
        for name in names:
            p = PurePosixPath(name)
            if p.is_absolute() or '..' in p.parts or '\\' in name or ':' in name:
                raise ValueError('Caminho ZIP recusado')
        manifest = json.loads(z.read('SHA256.json'))
        if set(names) != set(manifest) | {'SHA256.json'}:
            raise ValueError('Manifesto ZIP incompleto')
        for name, checksum in manifest.items():
            if digest(z.read(name)) != checksum:
                raise ValueError('Integridade ZIP divergente: ' + name)
        return verify(z.read)

def record_dependencies(destination, compiler):
    """Capture actual package owners/versions without assuming all tool licenses ship."""
    prefix = compiler.parent.parent
    entries = []
    for binary in sorted((destination / 'bin').glob('*.dll')):
        if binary.name == 'santafe-3.dll':
            continue
        origin = prefix / 'bin' / binary.name
        if not origin.is_file() or origin.read_bytes() != binary.read_bytes():
            raise ValueError('DLL externa não corresponde ao toolchain: ' + binary.name)
        package = subprocess.check_output(['pacman', '-Qqo', '/'+prefix.name+'/bin/'+binary.name], text=True).strip()
        if not re.fullmatch(r'[a-zA-Z0-9_.+\-]+', package):
            raise ValueError('Dono do pacote ambíguo: ' + binary.name)
        identity = subprocess.check_output(['pacman', '-Q', package], text=True).strip()
        metadata = subprocess.check_output(['pacman', '-Qi', package], text=True)
        entries.append(dict(arquivo='bin/'+binary.name, sha256=digest(binary.read_bytes()),
                            pacote=package, identidade=identity, metadados=metadata,
                            assinatura_propria=False))
    if len(entries) != 4:
        raise ValueError('Revisar dependências: quantidade de DLLs externas mudou')
    (destination / 'DEPENDENCIAS-MSYS2.json').write_text(json.dumps({
        'binarios': entries, 'versoes_capturadas': True, 'resolucao_fixada': False,
        'fontes_correspondentes_incluidas': False,
        'observacao': 'Inventário da construção; não declara reprodução byte a byte nem cumprimento integral da LGPL.'
    }, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

if __name__ == '__main__':
    import sys
    print('AVISOS_CONFERIDOS', verify_archive(Path(sys.argv[1])))
