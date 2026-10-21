#!/usr/bin/env python3
"""Recusa distribuição final com versões divergentes ou gates pendentes."""
import json
from pathlib import Path
import re
import argparse

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--preflight',action='store_true',help='confere versões; permite obter as evidências ainda pendentes, sem publicar')
args=parser.parse_args()

ROOT=Path(__file__).resolve().parents[1]
v=json.loads((ROOT/'operação/conjunto-versoes.json').read_text())
errors=[]
header=(ROOT/'src/lua.h').read_text()
actual='.'.join(re.search(r'#define SANTAFE_VERSION_'+part+r' "([^"]+)"',header)[1]
                for part in ('MAJOR','MINOR','PATCH'))
if actual!=v['nucleo']: errors.append('núcleo '+actual+' ainda não corresponde ao alvo '+v['nucleo'])
if 'VERSION := '+v['nucleo']+'\n' not in (ROOT/'Makefile').read_text(): errors.append('Makefile divergente')
if 'version = "'+v['sls']+'"' not in (ROOT/'ferramentas/sls/sls.fé').read_text(): errors.append('SLS ainda não promovido')
for editor,file in [('vscode','package.json'),('sublime','package-metadata.json')]:
    if json.loads((ROOT/'extensões'/editor/file).read_text())['version']!=v[editor]: errors.append(editor+' divergente')
if not args.preflight and (v.get('estado')!='homologado' or v.get('gates_pendentes')!=[]):
    errors.append('homologação pendente: '+', '.join(v.get('gates_pendentes',[])))
evidence=ROOT/'docs/HOMOLOGACAO-CONJUNTA.json'
if not args.preflight and not evidence.is_file(): errors.append('registro de evidências finais ausente')
elif not args.preflight:
    proof=json.loads(evidence.read_text())
    if any(proof.get(k)!=v[k] for k in ('nucleo','sls','bibliotecas','vscode','sublime')): errors.append('evidências de outras versões')
    for gate in ('macos','debian','wasm','vscode_host','sublime_host','visual','publicador','distribuicao'):
        if not isinstance(proof.get(gate),dict) or proof[gate].get('resultado')!='ok' or not proof[gate].get('evidencia'):
            errors.append('evidência não comprovada: '+gate)
if errors:
    raise SystemExit('Conjunto ainda não publicável:\n- '+'\n- '.join(errors))
print('Versões coerentes para pré-validação sem publicação.' if args.preflight else 'Versões e registro de homologação coerentes; não substitui a execução da bateria.')
