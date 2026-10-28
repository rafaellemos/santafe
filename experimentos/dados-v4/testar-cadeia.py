#!/usr/bin/env python3
"""Baterias de laboratório: logs preservados; nenhuma publicação/instalação global."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
assert (ROOT/'.laboratorio-dados4').is_file()
os.chdir(ROOT)
evidence=ROOT/'evidencias'; evidence.mkdir(exist_ok=True)
env={k:os.environ[k] for k in ('PATH','TMPDIR','LANG','LC_ALL') if k in os.environ}
env.update(GSETTINGS_BACKEND='memory',CFLAGS='-DSANTAFE_DADOS_EXPERIMENTAL -DLUA_USE_APICHECK')
tests=[('pacotes','testes/integracao/testar_pacotes.py'),
       ('cli','testes/integracao/testar_pacotes_cli.py'),
       ('https','testes/integracao/testar_pacotes_https.py'),
       ('catalogo','testes/integracao/testar_catalogo_bibliotecas.py'),
       ('formatos','experimentos/dados-v4/testar-formatos.py'),
       ('pacotes-memoria','testes/integracao/testar_pacotes_memoria.py'),
       ('sls-memoria','testes/integracao/testar_sls_memoria.py'),
       ('unicode','testes/integracao/testar_unicode.py'),
       ('gabaritos','testes/integracao/testar_gabaritos_unicode.py'),
       ('carteiro-fusos','testes/integracao/testar_carteiro_fusos.py')]
results=[]
for name,path in tests:
    if len(sys.argv)>1 and sys.argv[1]!=name: continue
    start=time.monotonic()
    with (evidence/('cadeia-'+name+'.log')).open('w') as log:
        proc=subprocess.Popen([sys.executable,path],cwd=ROOT,env=env,
                              stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try: code=proc.wait(timeout=180)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid,signal.SIGKILL); proc.wait(); code=124
    results.append(dict(teste=name,codigo=code,segundos=round(time.monotonic()-start,2)))
    (evidence/'cadeia.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
    print(('PASSOU' if code==0 else 'FALHOU'),name,flush=True)
    if code: print((evidence/('cadeia-'+name+'.log')).read_text()[-2500:],flush=True)
print(f'Baterias: {sum(x["codigo"]==0 for x in results)} aprovadas de {len(results)}.')
sys.exit(any(x['codigo'] for x in results))
