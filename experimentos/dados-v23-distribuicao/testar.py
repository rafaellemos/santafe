#!/usr/bin/env python3
"""Bateria da distribuição 3 candidata, com orçamento de disco e logs."""
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('etapa', choices=('compilar', 'regressao', 'bibliotecas', 'transacao', 'wasm'))
args = parser.parse_args()
assert (ROOT/'.laboratorio-dados23').is_file()
py = sys.executable
env = dict(os.environ, GSETTINGS_BACKEND='memory', SANTAFE_CANDIDATO=str(ROOT/'src/santafé'))
steps = {
    'compilar': [('fontes', [py, 'experimentos/dados-v3/conferir-fontes.py']),
                 ('compilacao', ['bash', 'experimentos/dados-v23-distribuicao/construir.sh'])],
    'regressao': [('iba', [py, 'experimentos/dados-v10/testar-iba.py']),
                  ('cadeia', [py, 'experimentos/dados-v10/testar.py']),
                  ('gerenciador', [py, 'testes/integracao/testar_pacotes.py']),
                  ('geracoes', [py, 'experimentos/dados-v6/testar-operacao.py', env.get('SANTAFE_ESTAVEL', '')])],
    'bibliotecas': [('matriz', [py, 'experimentos/dados-v3/testar-bibliotecas.py'])],
    'transacao': [('interrupcoes', [py, 'experimentos/dados-v23-distribuicao/testar-transacao.py']),
                  ('distribuicao', [py, 'experimentos/dados-v23-distribuicao/testar-distribuicao.py', env.get('SANTAFE_ESTAVEL', '')])],
    'wasm': [('wasm', ['bash', 'experimentos/dados-v7/construir-wasm.sh'])],
}[args.etapa]
out = ROOT/'evidencias'; out.mkdir(exist_ok=True)
report = out/('dados23-'+args.etapa+'.json')
result = {'resultado': 'EM_ANDAMENTO', 'sistema': sys.platform, 'testes': []}
for name, command in steps:
    if shutil.disk_usage(ROOT).free < 2048 * 1024**2:
        result['resultado'] = 'INTERROMPIDO_POR_ESPACO'
        report.write_text(json.dumps(result, indent=2)+'\n')
        raise SystemExit('Reserva mínima 2GiB; sem limpeza automática de outros ensaios')
    log = out/('dados23-'+args.etapa+'-'+name+'.log')
    start = time.monotonic()
    with log.open('wb') as f:
        p = subprocess.Popen(command, cwd=ROOT, env=env, stdout=f, stderr=subprocess.STDOUT,
                             start_new_session=True)
        try:
            code = p.wait(timeout=1200)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGTERM)
            try: p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(p.pid, signal.SIGKILL); p.wait()
            code = 124
    result['testes'].append({'teste': name, 'codigo': code, 'log': log.name,
                            'segundos': round(time.monotonic()-start, 2)})
    result['resultado'] = 'FALHOU' if code else 'EM_ANDAMENTO'
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(('FALHOU' if code else 'PASSOU'), name, flush=True)
    if code:
        print(log.read_text(errors='replace')[-5000:])
        raise SystemExit(code)
result['resultado'] = 'PASSOU'
report.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
