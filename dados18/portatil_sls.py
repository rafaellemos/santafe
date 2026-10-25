"""Same 39 SLS criteria, launched with no toolchain in PATH."""
from pathlib import Path
import json,sys,tempfile,time
root=Path(sys.argv[1]);exe=Path(sys.argv[2]);output=Path(sys.argv[3]);sys.path.insert(0,str(root/'testes/integracao'))
from sls.casos import CASOS
from sls.cliente import Cliente
result=[]
for case in CASOS:
 with tempfile.TemporaryDirectory(prefix='sls-portatil-') as tmp:
  c=Cliente([str(exe)],Path(tmp),prazo=15)
  try:
   c.inicie()
   if case['capacidade']:c.exija(case['capacidade'])
   case['execute'](c,{'repositorio':root,'medidas':{}})
   result.append({'id':case['id'],'passou':True})
  finally:c.feche()
output.write_text(json.dumps(result,ensure_ascii=True,indent=2),encoding='utf-8')
print('SLS_PORTATIL',len(result))
