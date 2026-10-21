#!/usr/bin/env python3
"""Monta entrega de fontes e lançador com hashes; não envia nem publica."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tarfile

ROOT=Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(source, distribution, destination):
    versions=json.loads((source/'operação/conjunto-versoes.json').read_text())
    version=versions['nucleo']
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?',version):
        raise ValueError('Versão inválida')
    names=['santafe-'+version+'.tar.gz','santafe-'+version+'.zip']
    subprocess.run(['python3',str(source/'testes/integracao/testar_distribuicao.py'),
                    *[str(distribution/n) for n in names]],check=True)
    with tarfile.open(distribution/names[0]) as archive:
        data=archive.extractfile('santafe-'+version+'/operação/conjunto-versoes.json').read()
        if json.loads(data)!=versions:
            raise ValueError('Pacote usa outro estado de versões/homologação')
    destination.mkdir(parents=True,exist_ok=False)
    sums={}
    for name in names:
        shutil.copyfile(distribution/name,destination/name)
        sums[name]=digest(destination/name)
    launcher=destination/('publicar-santafe-conjunto-'+version+'.sh')
    text='''#!/usr/bin/env bash
# Preparado de fontes auditadas; não obtém scripts pela rede.
# --preflight: compila e ensaia em /tmp sem instalar nem reiniciar serviços.
set -Eeuo pipefail
mode="${1:-publicar}"
[[ "$mode" == publicar || "$mode" == --preflight || "$mode" == --conferir ]] || { echo 'Use publicar, --preflight ou --conferir.' >&2; exit 2; }
[[ "$#" -le 1 ]] || exit 2
[[ "$mode" != publicar || "$EUID" -eq 0 ]] || { echo 'Publicação exige sudo bash; pré-validação não.' >&2; exit 2; }
payload="$(cd -- "$(dirname -- "$0")" && pwd)"
cd "$payload"
'''
    for name in names:
        q=shlex.quote(name)
        text+='[[ -f '+q+' && ! -L '+q+' ]] || { echo "Pacote ausente ou irregular." >&2; exit 1; }\n'
    # Python já é pré-requisito da validação. Evita diferenças BSD/GNU de sha256sum.
    text+="python3 - <<'SANTAFE_SOMAS'\nimport hashlib\n"
    text+='expected='+repr(sums)+'\n'
    text+='''for name,expected_hash in expected.items():
    result=hashlib.sha256()
    with open(name,'rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''): result.update(chunk)
    if result.hexdigest()!=expected_hash: raise SystemExit('SHA-256 divergente: '+name)
    print(name+': SHA-256 OK')
SANTAFE_SOMAS
'''
    text+='''[[ "$mode" != --conferir ]] || { echo 'ARQUIVOS_CONJUNTO_CONFERIDOS'; exit 0; }
work="$(mktemp -d /tmp/santafe-conjunto.XXXXXXXX)"
echo "Trabalho isolado e evidências: $work"
'''
    text+='tar --no-same-owner -xzf '+shlex.quote(names[0])+' -C "$work"\n'
    text+='export SANTAFE_CONJUNTO_PACOTES="$payload"\n'
    text+='exec bash "$work/'+('santafe-'+version)+'/operação/publicar-conjunto.sh" "$mode"\n'
    launcher.write_text(text,encoding='utf-8'); launcher.chmod(0o755)
    subprocess.run(['bash','-n',str(launcher)],check=True)
    sums[launcher.name]=digest(launcher)
    (destination/'SHA256SUMS').write_text(''.join(h+'  '+n+'\n' for n,h in sums.items()))
    (destination/'LEIA-ME.txt').write_text(
        'Entrega conjunta '+version+' — estado: '+versions['estado']+'\n'
        'Arquivos de preparação, não uma publicação concluída.\n'
        'Copie TAR, ZIP e lançador para o mesmo diretório /tmp do servidor.\n'
        'Conferência dos hashes sem extrair: bash /tmp/'+launcher.name+' --conferir\n'
        'Pré-validação isolada (sem sudo): bash /tmp/'+launcher.name+' --preflight\n'
        'Publicação somente após fechar os gates: sudo bash /tmp/'+launcher.name+'\n'
        'O publicador recusa versões sem homologação; não remova essa proteção.\n'
        'Nenhum GitHub/Marketplace/catálogo externo é atualizado por este comando.\n')
    print(destination)
    return launcher


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fonte',type=Path,default=ROOT)
    parser.add_argument('--distribuicao',type=Path,default=ROOT/'dist')
    parser.add_argument('--saida',type=Path,required=True)
    a=parser.parse_args()
    build(a.fonte.resolve(),a.distribuicao.resolve(),a.saida.resolve())
