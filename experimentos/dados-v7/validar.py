#!/usr/bin/env python3
"""Bateria de regressão privada, com logs reais e parada na primeira falha."""
import json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
assert (ROOT/'.laboratorio-dados7').is_file()
out=ROOT/'evidencias';out.mkdir(exist_ok=True)
env={k:v for k,v in os.environ.items() if k in ('PATH','TMPDIR','LANG','LC_ALL')}
env.update(GSETTINGS_BACKEND='memory',SANTAFE_CANDIDATO=str(ROOT/'src/santafé'))
boot='módulo.caminho="aplicativos/carteiro/fonte/?.fé;aplicativos/carteiro/fonte/?/ini.fé;bibs/bibf/?.fé;bibs/bibf/?/?.fé"; módulo.caminhoC="bibs/bibc/?/?.so"'
fe=[str(ROOT/'src/santafé'),'-E','-P','-e',boot]
py=[sys.executable]
tests=[('persistencia',py+['experimentos/dados-v7/testar-persistencia.py']),
       ('nucleo',fe+['experimentos/dados-v1/testar.fé']),
       ('onfe',fe+['experimentos/dados-v1/testar-onfe.fé']),
       ('fronteiras',fe+['experimentos/dados-v5/testar-fronteiras.fé']),
       ('arquivo-legado',fe+['testes/bibc/teste_arquivo.fé']),
       ('abi',py+['experimentos/dados-v3/testar-abi.py']),
       ('sls',py+['experimentos/dados-v2/testar-sls.py']),
       ('sls-onfe',py+['experimentos/dados-v7/testar-sls.py']),
       ('sls-carga',py+['experimentos/dados-v6/testar-carga-sls.py']),
       ('manual',py+['experimentos/dados-v6/testar-manual.py']),
       ('instalacao',py+['experimentos/dados-v5/testar-instalacao.py'])]
if len(sys.argv)>1: tests.append(('operacao',py+['experimentos/dados-v6/testar-operacao.py',sys.argv[1]]))
results=[]
for name,cmd in tests:
    start=time.monotonic()
    with (out/('dados7-'+name+'.log')).open('w') as log:
        p=subprocess.run(cmd,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=300)
    results.append({'teste':name,'codigo':p.returncode,'segundos':round(time.monotonic()-start,2)})
    (out/'dados7-regressao.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
    print(('PASSOU' if p.returncode==0 else 'FALHOU'),name,flush=True)
    if p.returncode:
        print((out/('dados7-'+name+'.log')).read_text()[-8000:]);raise SystemExit(1)
