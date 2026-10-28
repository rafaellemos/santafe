#!/usr/bin/env python3
"""Deriva dados.8 do pacote imutável dados.7, sempre em /tmp."""
from pathlib import Path
import hashlib, json, shutil, subprocess, tarfile, tempfile
ROOT=Path(__file__).resolve().parents[2]
archive=ROOT/'dist/candidato-dados-v7/santafe-candidato-dados.7-fontes.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='7c92e98d5ec6e62c1bfed08b0f7a906a004ed47223fae07ff13959279888cc80'
stage=Path(tempfile.mkdtemp(prefix='santafe-dados8-',dir='/tmp'))
print(stage,flush=True)
with tarfile.open(archive) as pack:
    for m in pack.getmembers():
        assert m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts
    pack.extractall(stage)
subprocess.run(['python3',str(stage/'experimentos/dados-v3/conferir-fontes.py')],check=True)
shutil.copytree(ROOT/'experimentos/dados-v8',stage/'experimentos/dados-v8',ignore=shutil.ignore_patterns('__pycache__'))
shutil.copy2(ROOT/'docs/CONTRATO-DADOS-ONFE.md',stage/'docs/CONTRATO-DADOS-ONFE.md')
shutil.copy2(ROOT/'docs/PLANO-PUBLICACAO-CONJUNTA-20261021.md',stage/'docs/PLANO-PUBLICACAO-CONJUNTA-20261021.md')
# O pacote anterior contém só o catálogo de APIs dos editores. Acrescentar
# os fontes/vendores locais, sem instalar as extensões nos perfis do usuário.
shutil.copytree(ROOT/'extensões',stage/'extensões',dirs_exist_ok=True,
    ignore=shutil.ignore_patterns('__pycache__','node_modules','.git','dist','*.vsix','*.sublime-package'))
(stage/'.laboratorio-dados8').write_text('Candidato privado; nenhuma instalação em produção.\n')
# Lexer anterior recompilado no laboratório: a migração usa valores/posições,
# não substituição textual de delimitadores no programa inteiro.
subprocess.run(['make','-C',str(stage/'src'),'-j2','generic','MYCFLAGS=-DSANTAFE_DADOS_EXPERIMENTAL -DLUA_USE_APICHECK'],check=True)
previous=stage/'nucleo-dados7'; shutil.copy2(stage/'src/santafé',previous)
changes=[]
for root in ('bibs','ferramentas','aplicativos','exemplos','testes','experimentos'):
    for p in sorted((stage/root).rglob('*')):
        if p.suffix not in ('.fé','.onfé') or 'dados-v8' in p.parts: continue
        if '``' not in p.read_text(): continue
        result=subprocess.run([str(previous),'-E','-P',str(stage/'experimentos/dados-v8/migrar-candidato.fé'),str(p)],capture_output=True,text=True,check=True)
        value=json.loads(result.stdout)
        if value['alterações']:
            p.write_text(value['texto']); changes.append({'arquivo':str(p.relative_to(stage)),'colares':value['alterações']})
(stage/'MIGRACAO-COLARES8.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n')
subprocess.run(['python3',str(stage/'experimentos/dados-v8/aplicar.py')],check=True)
subprocess.run(['make','-C',str(stage/'src'),'clean'],check=True)
print('CANDIDATO_PREPARADO',stage,flush=True)
