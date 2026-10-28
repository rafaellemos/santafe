#!/usr/bin/env python3
"""Matriz isolada; registra falhas/ignorados separadamente, sem instalações."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
assert (ROOT/'.laboratorio-dados3').is_file()
os.chdir(ROOT)
env = {k: os.environ[k] for k in ('PATH','TMPDIR','LANG','LC_ALL') if k in os.environ}
env['GSETTINGS_BACKEND'] = 'memory'
bootstrap = 'módulo.caminho="bibs/bibf/?.fé;bibs/bibf/?/?.fé"; módulo.caminhoC="bibs/bibc/?/?.so"'
results = []
evidence = ROOT/'evidencias'; evidence.mkdir(exist_ok=True)

def run(command, variables=None, timeout=30):
    p = subprocess.Popen(command, cwd=ROOT, env={**env, **(variables or {})},
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
    try:
        output = p.communicate(timeout=timeout)[0]
        return p.returncode, output.decode('utf-8', errors='replace')
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        return 124, p.communicate()[0].decode('utf-8', errors='replace') + '\nTEMPO LIMITE\n'

with tempfile.TemporaryDirectory(prefix='santafe-dados3-chave-') as tmp:
    key = str(Path(tmp)/'ensaio.pem')
    subprocess.run(['openssl','genpkey','-algorithm','RSA','-pkeyopt','rsa_keygen_bits:2048','-out',key],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
    env['SANTAFE_TESTE_DKIM_CHAVE'] = key
    env['NOMES_DNSSEC_CHAVE_TESTE'] = key
    tests = sorted([*ROOT.glob('testes/bibf/teste_*.f*'), *ROOT.glob('testes/bibc/teste_*.f*')])
    for path in tests:
        relative = str(path.relative_to(ROOT))
        if len(sys.argv)>1 and sys.argv[1] not in relative:
            continue
        extra = {}
        if path.name == 'teste_correio_configuração_bancos.fé':
            extra = dict(CORREIO_DEPOSITO='/var/lib/santafé/correio', SANTAFE_MARIADB_BANCO='principal_teste',
                CORREIO_BANCOS_ADICIONAIS='domínio.example|SECUNDARIO|/var/lib/correio-clientes/secundario/correio',
                SECUNDARIO_MARIADB_HOST='127.0.0.1',SECUNDARIO_MARIADB_PORTA='3306',
                SECUNDARIO_MARIADB_USUARIO='teste',SECUNDARIO_MARIADB_SENHA='teste',SECUNDARIO_MARIADB_BANCO='secundario_teste')
        elif path.name == 'teste_correio_configuração_multidominio.fé':
            extra = dict(CORREIO_DKIM_DOMINIO='xn--santaf-gva.dev.br', CORREIO_DKIM_SELETOR='santafe2026',
                CORREIO_DKIM_CHAVE='/tmp/santafe.pem', CORREIO_DKIM_IDENTIDADES='xn--domnio-5va.example|secundario2026|/tmp/secundario.pem')
        start = time.monotonic()
        rc, output = run([str(ROOT/'src/santafé'),'-E','-P','-e',bootstrap,relative],extra)
        status = 'FALHOU' if rc else ('IGNORADO' if 'IGNORADO:' in output else 'PASSOU')
        item = dict(teste=relative, estado=status, codigo=rc, segundos=round(time.monotonic()-start,2), saida=output)
        results.append(item)
        print(status,relative,flush=True)
        if rc: print(output[-1600:], flush=True)
        (evidence/'bibliotecas.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
print({s:sum(r['estado']==s for r in results) for s in ('PASSOU','FALHOU','IGNORADO')})
sys.exit(any(r['estado']=='FALHOU' for r in results))
