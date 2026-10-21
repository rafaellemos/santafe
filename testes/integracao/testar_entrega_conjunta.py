#!/usr/bin/env python3
"""Confere o lançador real com uma distribuição existente, sem publicar/build."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser()
parser.add_argument('--distribuicao',type=Path,default=ROOT/'dist')
args=parser.parse_args()
spec=importlib.util.spec_from_file_location('entrega',ROOT/'operação/preparar-publicacao-conjunta.py')
module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
version=json.loads((ROOT/'operação/conjunto-versoes.json').read_text())['nucleo']

with tempfile.TemporaryDirectory(prefix='santafe-entrega-') as directory:
    root=Path(directory); bundle=root/'arquivos com espaços'
    launcher=module.build(ROOT,args.distribuicao,bundle)
    def run(*argv,ok):
        result=subprocess.run(['bash',str(launcher),*argv],capture_output=True,text=True,timeout=20)
        assert (result.returncode==0)==ok,result.stdout+result.stderr
        return result
    assert 'ARQUIVOS_CONJUNTO_CONFERIDOS' in run('--conferir',ok=True).stdout
    run('--inexistente',ok=False); run('--conferir','extra',ok=False)
    for suffix in ('tar.gz','zip'):
        file=bundle/('santafe-'+version+'.'+suffix)
        original=file.read_bytes()
        file.write_bytes(original+b'adulterado')
        run('--conferir',ok=False)
        file.write_bytes(original)
        regular=root/('alvo-'+suffix); file.rename(regular); file.symlink_to(regular)
        run('--conferir',ok=False)
        file.unlink(); regular.rename(file)
    run('--conferir',ok=True)
    print('Entrega: hashes reais, TAR/ZIP idênticos, caminhos com espaços e links/adulteração recusados: ok')
