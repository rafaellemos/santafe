#!/usr/bin/env python3
"""Distribuição local explícita: fonte, executáveis isolados, editores e evidências."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'dist/candidato-dados-v2'
files=set()
def add(path):
    path=ROOT/path
    assert path.is_file() and not path.is_symlink(), path
    files.add(path)

for pattern in ('src/*.c','src/*.h','src/Makefile','experimentos/dados-v1/*.fé',
    'experimentos/dados-v1/*.onfé','experimentos/dados-v1/*.py',
    'experimentos/dados-v1/*.c','experimentos/dados-v1/*.js',
    'experimentos/dados-v2/*','ferramentas/sls/*.fé','ferramentas/sls/*.json',
    'ferramentas/sls/*.c','testes/integracao/sls/*'):
    for path in ROOT.glob(pattern):
        if path.is_file(): add(path)

for folder in ('extensões/vscode','extensões/sublime',
               'dist/candidato-dados-v2/editores','dist/candidato-dados-v2/evidencias'):
    for path in (ROOT/folder).rglob('*'):
        if not path.is_file() or any(p in ('__pycache__','node_modules','.git','dist')
             for p in path.relative_to(ROOT/folder).parts): continue
        if path.suffix in ('.pyc','.pyo','.DS_Store'): continue
        add(path)

# Corpus estável usado pelo teste de análise, não executado no dialeto candidato.
tracked=subprocess.check_output(['git','ls-files','-z','--','bibs','ferramentas','aplicativos'],cwd=ROOT)
for name in tracked.decode().split('\0'):
    if name.endswith('.fé'): add(Path(name))
for name in ('LICENSE','docs/CONTRATO-DADOS-ONFE.md',
    'dist/candidato-dados-v2/santafé-dados','dist/candidato-dados-v2/santafec-dados',
    'dist/candidato-dados-v2-baseline/santafé-dados',
    'testes/bibf/teste_json.fé','testes/metatabelas.fé',
    'testes/bibf/teste_gabarito_unicode.fé','testes/bibf/teste_sls_analisador.fé',
    'testes/integracao/testar_sls_aceitacao.py','testes/integracao/testar_sls_infraestrutura.py',
    'testes/integracao/testar_sls_incremental.py','testes/integracao/testar_analise_c.py',
    'testes/integracao/testar_sls_semantica.py','testes/integracao/testar_sls_cancelamento.py'):
    add(Path(name))
files=sorted(files)
entries=[]
for path in files:
    entries.append('{arquivo='+json.dumps(str(path.relative_to(ROOT)),ensure_ascii=False)+
        ',sha256="'+hashlib.sha256(path.read_bytes()).hexdigest()+'"}')
manifest=OUT/'MANIFESTO.onfé'
manifest.write_text('{candidato="dados.2",experimental=verdadeiro,plataforma="macOS x86_64",arquivos=[\n'+
                    ',\n'.join(entries)+']}\n')
files.append(manifest)
archive=OUT/'santafe-candidato-dados.2.tar.gz'
with tarfile.open(archive,'w:gz',format=tarfile.PAX_FORMAT) as tar:
    for path in files:
        info=tar.gettarinfo(str(path),arcname='santafe-candidato-dados.2/'+str(path.relative_to(ROOT)))
        info.uid=info.gid=0; info.uname=info.gname=''
        with path.open('rb') as stream: tar.addfile(info,stream)
with tarfile.open(archive) as tar:
    assert len(tar.getmembers())==len(files)
    for member,path in zip(tar.getmembers(),files):
        assert member.isfile() and not PurePosixPath(member.name).is_absolute()
        assert '..' not in PurePosixPath(member.name).parts
        assert hashlib.sha256(tar.extractfile(member).read()).digest()==hashlib.sha256(path.read_bytes()).digest()
digest=hashlib.sha256(archive.read_bytes()).hexdigest()
(OUT/'SHA256SUMS').write_text(digest+'  '+archive.name+'\n')
print(archive)
print('SHA256',digest)
print('ARQUIVOS',len(files))
