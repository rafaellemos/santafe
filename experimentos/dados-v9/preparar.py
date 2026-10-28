#!/usr/bin/env python3
"""Deriva dados.9 do arquivo selado dados.8; jamais modifica a produção."""
from pathlib import Path
import hashlib,json,shutil,subprocess,tarfile,tempfile
ROOT=Path(__file__).resolve().parents[2]
archive=ROOT/'dist/candidato-dados-v8/santafe-candidato-dados.8-fontes.tar.gz'
expected='f95592a0737d663f7a70d01a70aa96fda9c83a111c34cdd0d2f8287d5b75cabb'
if hashlib.sha256(archive.read_bytes()).hexdigest()!=expected:raise SystemExit('Base dados.8 divergente')
stage=Path(tempfile.mkdtemp(prefix='santafe-dados9-',dir='/tmp')).resolve()
with tarfile.open(archive) as pack:
 for m in pack.getmembers():
  if not m.isfile() or Path(m.name).is_absolute() or '..' in Path(m.name).parts:raise SystemExit('Membro inválido')
 pack.extractall(stage)
subprocess.run(['python3',str(stage/'experimentos/dados-v3/conferir-fontes.py')],check=True)
before=json.loads((stage/'MANIFESTO-FONTES.json').read_text())
def change(name,old,new,count=1):
 p=stage/name;t=p.read_text()
 if t.count(old)!=count:raise RuntimeError((name,old,t.count(old)))
 p.write_text(t.replace(old,new))
change('extensões/vscode/aparencia.js',
 'const t=vscode.window.createTextEditorDecorationType({color:cor, fontStyle:fonte});',
 '''// Estilo por tema evita o caminho de métricas que oculta a decoração
      // no renderer 1.142. Cor e normal/italic permanecem explícitos.
      const t=vscode.window.createTextEditorDecorationType({
        color:cor, light:{fontStyle:fonte}, dark:{fontStyle:fonte}
      });''')
shutil.copy2(ROOT/'extensões/vscode/testes/testar_api_paletas.js',stage/'extensões/vscode/testes/testar_api_paletas.js')
change('src/lua.h','"dados.8"','"dados.9"')
change('ferramentas/sls/sls.fé','"1.0.0-dados.8"','"1.0.0-dados.9"')
p=stage/'experimentos/dados-v2/editores.py'
p.write_text(p.read_text().replace('dados-v8/editores','dados-v9/editores').replace('dados.8','dados.9').replace('0.0.8','0.0.9').replace('EDITORES_DADOS_8_OK','EDITORES_DADOS_9_OK'))
p=stage/'experimentos/dados-v2/testar-editores.js'
p.write_text(p.read_text().replace('dados-v8/editores','dados-v9/editores'))
p=stage/'docs/manual.html';p.write_text(p.read_text().replace('dados.8','dados.9'))
for name in ('testar-editores.js','testar-recorte-sublime.py'):
 p=stage/'experimentos/dados-v8'/name
 p.write_text(p.read_text().replace('dados-v8/editores','dados-v9/editores'))
for name in ('Makefile', 'instalar.sh', 'experimentos/dados-v3/testar-wasm.js', 'experimentos/dados-v5/testar-instalacao.py', 'experimentos/dados-v6/testar-operacao.py', 'experimentos/dados-v6/operacao.py', 'experimentos/dados-v8/visual.py'):
 p=stage/name;p.write_text(p.read_text().replace('dados.8','dados.9'))
shutil.copytree(ROOT/'experimentos/dados-v9',stage/'experimentos/dados-v9',ignore=shutil.ignore_patterns('__pycache__'))
shutil.copy2(ROOT/'docs/CONTRATO-DADOS-ONFE.md',stage/'docs/CONTRATO-DADOS-ONFE.md')
shutil.copy2(ROOT/'docs/PLANO-PUBLICACAO-CONJUNTA-20261021.md',stage/'docs/PLANO-PUBLICACAO-CONJUNTA-20261021.md')
(stage/'.laboratorio-dados9').write_text('Somente homologação; nenhuma instalação em produção.\n')
changes=[]
for name,sha in before.items():
 p=stage/name;new=hashlib.sha256(p.read_bytes()).hexdigest()
 if new!=sha:changes.append({'arquivo':name,'antes':sha,'depois':new})
(stage/'DELTA-DADOS9.json').write_text(json.dumps({'base_sha256':expected,'alterados':changes},ensure_ascii=False,indent=2)+'\n')
print('CANDIDATO_PREPARADO',stage,flush=True)
