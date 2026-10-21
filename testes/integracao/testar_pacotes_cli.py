#!/usr/bin/env python3
"""Real public commands, independent projects, installed/source executable."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
from testar_pacotes import fixture, ROOT

parser=argparse.ArgumentParser()
parser.add_argument('--binario',type=Path,default=ROOT/'src/santafé')
args=parser.parse_args(); binary=args.binario.resolve()
env={k:v for k,v in os.environ.items() if not k.startswith(('LUA_','SANTAFE_'))}
def run(cwd,*arguments,success=True):
    p=subprocess.run([str(binary),*map(str,arguments)],cwd=cwd,env=env,text=True,capture_output=True,timeout=35)
    assert (p.returncode==0)==success,p.stdout+p.stderr
    return p

with tempfile.TemporaryDirectory(prefix='santafe-cli-pacotes-') as temporary:
    root=Path(temporary); repo=root/'repositório'; repo.mkdir()
    source=root/'fonte'; fixture(source)
    a=root/'projeto A'; b=root/'projeto B'; a.mkdir(); b.mkdir()
    package=root/'exemplo.sfp'
    run(root,'empacote',source,package)
    run(root,'catalogo',repo,package)
    run(a,'instale','exemplo','^1.0.0','--repositorio-local',repo)
    run(a,'-e','garanta((importe "exemplo").valor==42)')
    manifest=json.loads((source/'santafe.json').read_text()); manifest['versao']='1.1.0'
    (source/'santafe.json').write_text(json.dumps(manifest))
    (source/'bibf/exemplo.fé').write_text('retorne {valor=99}')
    package2=root/'exemplo2.sfp'
    run(root,'empacote',source,package2); run(root,'catalogo',repo,package2)
    run(b,'instale','exemplo','^1.0.0','--repositorio-local',repo)
    run(b,'-e','garanta((importe "exemplo").valor==99)')
    run(a,'instale','--repositorio-local',repo)
    run(a,'-e','garanta((importe "exemplo").valor==42)')
    run(a,'instale','--atualizar','--repositorio-local',repo)
    run(a,'-e','garanta((importe "exemplo").valor==99)')
    lock=(a/'santafe.lock').read_bytes()
    run(a,'instale','--travado','--repositorio-local',repo)
    assert lock==(a/'santafe.lock').read_bytes()
    # Source file integrity is checked when importing, not just installing.
    state=json.loads((a/'.santafe/estado.json').read_text())
    sourcefile=a/'.santafe/geracoes'/state['geracao']/'pacotes/exemplo/bibf/exemplo.fé'
    sourcefile.write_text('retorne {valor=-1}')
    run(a,'-e','importe "exemplo"',success=False)
    run(a,'-P','-e','mostre("núcleo independente do projeto")')
    run(a,'instale','--sem-rede','--repositorio-local',repo)
    run(a,'-e','garanta((importe "exemplo").valor==99)')
    run(a,'instale','--opcao-inexistente',success=False)
    print('CLI bibliotecas: empacote/catalogo/instale, dois projetos, lock, atualização explícita e integridade no importe: ok')
