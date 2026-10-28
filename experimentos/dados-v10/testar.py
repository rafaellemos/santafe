#!/usr/bin/env python3
"""Regressão dados.22, sem produção; falhas nunca são tratadas como aprovação."""
from pathlib import Path
import json,os,subprocess,sys,time
root=Path(__file__).resolve().parents[2]
if not (root/'.laboratorio-dados10').is_file():raise SystemExit('Exige laboratório dados.22')
for k in ('SANTAFE_ESTAVEL','SANTAFE_DADOS7'):
 if not Path(os.environ.get(k,'/inexistente')).is_file():raise SystemExit('Informe '+k)
out=root/'evidencias';out.mkdir(exist_ok=True)
py=sys.executable
steps=[('colares',[py,'experimentos/dados-v8/testar-colares.py']),('fontes',[py,'experimentos/dados-v8/testar-fontes.py']),('sls-incremental',[py,'experimentos/dados-v8/testar-sls.py']),('regressao',[py,'experimentos/dados-v7/validar.py']),('kits',[py,'experimentos/dados-v2/editores.py']),('cores',['node','extensões/vscode/testes/testar_api_paletas.js']),('editores25',['node','experimentos/dados-v2/testar-editores.js','experimentos/dados-v15/gramaticas-vscode']),('editores45',['node','experimentos/dados-v8/testar-editores.js']),('sublime17',[py,'experimentos/dados-v6/testar-recorte-sublime.py','dist/candidato-dados-v22/editores']),('sublime7',[py,'experimentos/dados-v8/testar-recorte-sublime.py'])]
results=[]
for name,cmd in steps:
 start=time.monotonic()
 with (out/('dados10-'+name+'.log')).open('w') as log:
  p=subprocess.run(cmd,cwd=root,stdout=log,stderr=subprocess.STDOUT,timeout=600)
 results.append({'teste':name,'codigo':p.returncode,'segundos':round(time.monotonic()-start,2)})
 (out/'dados10-regressao.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
 print(('PASSOU' if p.returncode==0 else 'FALHOU'),name,flush=True)
 if p.returncode:
  print((out/('dados10-'+name+'.log')).read_text()[-6000:]);raise SystemExit(p.returncode)
