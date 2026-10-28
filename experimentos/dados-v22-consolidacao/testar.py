#!/usr/bin/env python3
"""Regressão conjunta isolada. Registro explícito de falhas, sem efeitos em produção."""
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
parser.add_argument('--etapa', choices=('compilar', 'regressao', 'bibliotecas', 'banco', 'aplicativos', 'wasm'), required=True)
parser.add_argument('--reserva-mib', type=int, default=2048)
args = parser.parse_args()
assert (ROOT/'.laboratorio-dados22').is_file()
assert args.reserva_mib >= 2048
out = ROOT/'evidencias'; out.mkdir(exist_ok=True)
py = sys.executable
env = dict(os.environ, GSETTINGS_BACKEND='memory', SANTAFE_CANDIDATO=str(ROOT/'src/santafé'))
if args.etapa == 'regressao':
    for key in ('SANTAFE_ESTAVEL', 'SANTAFE_DADOS7'):
        if not Path(env.get(key, '/inexistente')).is_file():
            raise SystemExit('Informe a referência real: ' + key)
steps = {
    'compilar': [
        ('integridade', [py, 'experimentos/dados-v3/conferir-fontes.py']),
        ('nucleo', ['bash', 'experimentos/dados-v3/construir.sh']),
        ('sls-nativo', ['make', '-C', 'ferramentas/sls', 'CFLAGS=-O2 -Wall -Wextra -DSANTAFE_DADOS_EXPERIMENTAL -DLUA_USE_APICHECK']),
        ('pacotes-nativo', ['make', '-C', 'ferramentas/pacotes', 'CFLAGS=-O2 -Wall -Wextra -DSANTAFE_DADOS_EXPERIMENTAL -DLUA_USE_APICHECK']),
    ],
    'regressao': [
        ('iba', [py, 'experimentos/dados-v10/testar-iba.py']),
        ('cadeia', [py, 'experimentos/dados-v10/testar.py']),
        ('gerenciador', [py, 'testes/integracao/testar_pacotes.py']),
        ('reversao', [py, 'experimentos/dados-v6/testar-operacao.py', env.get('SANTAFE_ESTAVEL', '')]),
    ],
    'bibliotecas': [('matriz', [py, 'experimentos/dados-v3/testar-bibliotecas.py'])],
    'banco': [('mariadb-descartavel', [py, 'experimentos/dados-v3/testar-mariadb.py'])],
    'aplicativos': [('processos-isolados', [py, 'experimentos/dados-v5/testar-aplicativos.py'])],
    'wasm': [('compilar-executar', ['bash', 'experimentos/dados-v7/construir-wasm.sh'])],
}[args.etapa]
result = {'etapa': args.etapa, 'sistema': sys.platform, 'resultado': 'EM_ANDAMENTO',
          'producao_alterada': False, 'testes': []}
report = out/('consolidacao22-'+args.etapa+'.json')
for name, command in steps:
    free = shutil.disk_usage(ROOT).free
    if free < args.reserva_mib * 1024**2:
        result.update(resultado='INTERROMPIDO_POR_ESPACO', livre_bytes=free)
        report.write_text(json.dumps(result, indent=2)+'\n')
        raise SystemExit('Reserva de disco insuficiente; não iniciar ' + name)
    start = time.monotonic()
    log = out/('consolidacao22-'+args.etapa+'-'+name+'.log')
    with log.open('wb') as stream:
        try:
            proc = subprocess.Popen(command, cwd=ROOT, env=env, stdout=stream,
                                    stderr=subprocess.STDOUT, start_new_session=True)
            code = proc.wait(timeout=1200)
        except subprocess.TimeoutExpired:
            # Encerra somente o grupo criado por esta etapa, inclusive filhos.
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
            code = 124
    result['testes'].append({'teste': name, 'codigo': code, 'comando': command,
                             'segundos': round(time.monotonic()-start, 2), 'log': log.name})
    result['resultado'] = 'FALHOU' if code else 'EM_ANDAMENTO'
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(('FALHOU' if code else 'PASSOU'), args.etapa, name, flush=True)
    if code:
        print(log.read_text(errors='replace')[-6000:])
        raise SystemExit(code)
result['resultado'] = 'PASSOU'
report.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
