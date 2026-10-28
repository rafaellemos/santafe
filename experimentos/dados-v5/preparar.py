#!/usr/bin/env python3
"""Cria fonte candidata em diretório novo; não modifica a instalação estável."""
from pathlib import Path
import hashlib,json,shutil,subprocess,tarfile,tempfile
ROOT=Path(__file__).resolve().parents[2]
archive=ROOT/'dist/candidato-dados-v4/santafe-candidato-dados.4-fontes.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='bab1f596e2c1ea63019a4debfa881731a70d078e6bc08cae5e4379e06920103f'
stage=Path(tempfile.mkdtemp(prefix='santafe-dados5-',dir='/tmp'))
with tarfile.open(archive) as package:
    for m in package.getmembers():
        assert m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts
    package.extractall(stage)
subprocess.run(['python3',str(stage/'experimentos/dados-v3/conferir-fontes.py')],check=True)
for name in ('Makefile','instalar.sh','ferramentas/instalar-arquivos.sh','ferramentas/desinstalar-arquivos.sh',
             'ferramentas/sls/santafé-sls','testes/integracao/testar_instalador.py'):
    p=stage/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,p)
shutil.copytree(ROOT/'experimentos/dados-v5',stage/'experimentos/dados-v5',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
changes=[]
def change(name,before,after,count=1):
    p=stage/name;t=p.read_text();assert t.count(before)==count,(name,before,t.count(before))
    p.write_text(t.replace(before,after));changes.append(dict(arquivo=name,antes=before,depois=after))
change('src/lua.h','"dados.4"','"dados.5"')
change('ferramentas/sls/sls.fé','1.0.0-dados.4','1.0.0-dados.5')
change('ferramentas/sls/sls.fé','diretórioSLS.."/../../experimentos/dados-v1/onfé.fé"','diretórioSLS.."/onfé.fé"')
shutil.copy2(stage/'experimentos/dados-v1/onfé.fé',stage/'ferramentas/sls/onfé.fé')
change('ferramentas/instalar-arquivos.sh','ferramentas/sls/api-publica.json "$prefix/share',
       'ferramentas/sls/api-publica.json ferramentas/sls/estrutura.fé ferramentas/sls/onfé.fé "$prefix/share')
change('ferramentas/desinstalar-arquivos.sh','transporte.fé api-publica.json nativo.so;',
       'transporte.fé api-publica.json estrutura.fé onfé.fé nativo.so;')
# Ferramentas de laboratório, sem publicar mudança do contrato estável.
(stage/'.laboratorio-dados5').write_text('somente prefixos e bancos descartáveis\n')
(stage/'MIGRACAO-APLICATIVOS.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n')
subprocess.run(['python3',str(stage/'experimentos/dados-v5/aplicar.py'),str(stage)],check=True)
print(stage)
