#!/usr/bin/env python3
"""Deriva fontes 22 da entrega Windows 21 conferida. Não instala nem publica."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tarfile

BASE_SHA256 = '2aaa87ecd47749da0695e45b55b08e16783618c204261a56e283cfbc0ca8d72a'
HERE = Path(__file__).resolve().parent


def preparar(archive, destination):
    if hashlib.sha256(archive.read_bytes()).hexdigest() != BASE_SHA256:
        raise ValueError('A base selada dados.21 divergiu')
    if destination.exists():
        raise ValueError('O destino deve ser novo')
    with tarfile.open(archive) as pack:
        files = {}
        for item in pack.getmembers():
            rel = PurePosixPath(item.name)
            if (not item.isfile() or rel.is_absolute() or '..' in rel.parts
                    or item.name in files or item.size > 32 * 1024**2):
                raise ValueError('Membro inseguro: ' + item.name)
            files[item.name] = (pack.extractfile(item).read(), item.mode & 0o755)
    if len(files) != 880:
        raise ValueError('Quantidade de fontes inesperada')
    destination.mkdir(parents=True, mode=0o700)
    for name, (data, mode) in files.items():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        target.chmod(mode)
    # Somente identidades da cadeia ativa. Histórico 1..21 permanece intacto.
    active = [
        'src/lua.h', 'ferramentas/sls/sls.fé', 'ferramentas/pacotes/cli.fé',
        'Makefile', 'instalar.sh', 'docs/manual.html',
        'experimentos/dados-v2/editores.py', 'experimentos/dados-v2/testar-editores.js',
        'experimentos/dados-v3/testar-wasm.js', 'experimentos/dados-v5/testar-instalacao.py',
        'experimentos/dados-v6/operacao.py', 'experimentos/dados-v6/testar-operacao.py',
        'experimentos/dados-v8/testar-editores.js',
        'experimentos/dados-v8/testar-recorte-sublime.py',
        'experimentos/dados-v10/testar.py',
    ]
    changes = []
    for name in active:
        target = destination / name
        before = target.read_bytes()
        text = before.decode('utf-8')
        text = re.sub(r'dados\.(?:15|18|21)\b', 'dados.22', text)
        text = text.replace('0.0.15', '0.0.22')
        text = text.replace('dist/candidato-dados-v15', 'dist/candidato-dados-v22')
        # Gramáticas de referência continuam as do corpus conferido dados15.
        target.write_text(text, encoding='utf-8')
        after = target.read_bytes()
        if before != after:
            changes.append({'arquivo': name, 'antes': hashlib.sha256(before).hexdigest(),
                            'depois': hashlib.sha256(after).hexdigest()})
    # Invariantes de proteção preservados; não reabilitar o publicador 2.1.
    assert '$(error Candidato dados.22' in (destination/'Makefile').read_text()
    assert 'instalação pública indisponível' in (destination/'instalar.sh').read_text()
    for source in sorted((HERE/'overlay').rglob('*')):
        if not source.is_file():
            continue
        name = source.relative_to(HERE/'overlay').as_posix()
        target = destination/name
        before = target.read_bytes()
        target.write_bytes(source.read_bytes())
        changes.append({'arquivo': name, 'antes': hashlib.sha256(before).hexdigest(),
                        'depois': hashlib.sha256(target.read_bytes()).hexdigest(),
                        'motivo': 'correção isolada conferida na consolidação'})
    (destination/'.laboratorio-dados22').write_text('Homologação isolada; produção preservada.\n')
    recipe = destination/'experimentos/dados-v22-consolidacao'
    recipe.mkdir()
    for name in ('preparar.py', 'testar.py', 'LEIA-ME.md'):
        (recipe/name).write_bytes((HERE/name).read_bytes())
    for source in sorted((HERE/'overlay').rglob('*')):
        if source.is_file():
            target = recipe/'overlay'/source.relative_to(HERE/'overlay')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
    (destination/'CONSOLIDACAO22.json').write_text(json.dumps({
        'candidato': 'dados.22', 'base_sha256': BASE_SHA256, 'base_arquivos': len(files),
        'alterados': changes, 'semantica_alterada': False,
        'producao_alterada': False, 'publicacao_permitida': False,
    }, ensure_ascii=False, indent=2)+'\n')
    manifest = {str(p.relative_to(destination)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(destination.rglob('*')) if p.is_file() and p.name != 'MANIFESTO-FONTES.json'}
    (destination/'MANIFESTO-FONTES.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    print('CONSOLIDACAO22_PREPARADA', destination, len(manifest), 'fontes')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base', type=Path)
    parser.add_argument('destino', type=Path)
    args = parser.parse_args()
    preparar(args.base.resolve(), args.destino.absolute())
