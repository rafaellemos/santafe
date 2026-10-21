#!/usr/bin/env python3
"""Empacota somente a revisão textual; não envia nem instala."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def build(out):
    publisher = load(ROOT / 'operação/publicar-textos-2.1.0.py', 'textos')
    original = load(ROOT / 'operação/preparar-conjunto.py', 'conjunto')
    out.mkdir(parents=True, exist_ok=False)
    manual = original.cache((ROOT / 'docs/manual.html').read_text(), '2.1.0')
    publisher.check_manual_revision(manual)
    (out / 'manual.html').write_text(manual, encoding='utf-8')
    for src, dst in ((ROOT / 'ferramentas/pacotes/cli.fé', 'cli.fé'),
                     (ROOT / 'operação/publicar-textos-2.1.0.py', 'publicar-textos.py'),
                     (ROOT / 'operação/fechamento-2.0.py', 'transacao.py')):
        shutil.copyfile(src, out / dst)
    hashes = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in out.iterdir()}
    manifest = dict(revisao=publisher.REVISION, nucleo='2.1.0', sls='1.0.0', bibliotecas='1.0.0',
                    arquivos=hashes, antes={'manual.html': publisher.BEFORE_MANUAL, 'cli.fé': publisher.BEFORE_CLI},
                    destinos=[str(publisher.PUBLIC), str(publisher.MIRROR)],
                    somente_validacao=['cli.fé'],
                    reinicia_servicos=False, altera_downloads=False)
    (out / 'manifesto.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    hashes['manifesto.json'] = hashlib.sha256((out / 'manifesto.json').read_bytes()).hexdigest()
    launcher = out / 'publicar-textos-santafe-2.1.0-r2.sh'
    launcher.write_text('''#!/usr/bin/env bash
set -Eeuo pipefail
mode="${1:-publicar}"
[[ "$#" -le 1 ]] || exit 2
[[ "$mode" == publicar || "$mode" == --preflight ]] || exit 2
[[ "$mode" != publicar || "$EUID" -eq 0 ]] || { echo 'Use sudo bash; --preflight não exige sudo.' >&2; exit 2; }
payload="$(cd -- "$(dirname -- "$0")" && pwd)"
# Os bytes verificados são copiados uma única vez para diretório privado.
# Não há extração de tar nem execução de scripts obtidos pela rede.
stage="$(python3 - "$payload" <<'SANTAFE_TEXTOS'
import hashlib, pathlib, sys, tempfile
root=pathlib.Path(sys.argv[1])
expected=''' + repr(hashes) + '''
contents={}
for name,digest in expected.items():
    path=root/name
    if path.is_symlink() or not path.is_file(): raise SystemExit('Arquivo irregular: '+name)
    data=path.read_bytes()
    if hashlib.sha256(data).hexdigest()!=digest: raise SystemExit('SHA-256 divergente: '+name)
    contents[name]=data
stage=pathlib.Path(tempfile.mkdtemp(prefix='santafe-textos-verificados-',dir='/tmp'))
for name,data in contents.items():
    file=stage/name
    file.write_bytes(data)
    file.chmod(0o600)
print(stage)
SANTAFE_TEXTOS
)"
echo "Entrega conferida: $stage"
python3 "$stage/publicar-textos.py" "$mode"
''', encoding='utf-8')
    launcher.chmod(0o755)
    subprocess.run(['bash', '-n', launcher], check=True)
    hashes[launcher.name] = hashlib.sha256(launcher.read_bytes()).hexdigest()
    (out / 'SHA256SUMS').write_text(''.join(f'{value}  {name}\n' for name, value in hashes.items()))
    print(out)


if __name__ == '__main__':
    import sys
    sys.dont_write_bytecode = True
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--saida', type=Path, required=True)
    build(parser.parse_args().saida.resolve())
