#!/usr/bin/env python3
import json
from pathlib import Path
import platform
import subprocess
import tempfile
ROOT=Path(__file__).resolve().parents[2]
assert (ROOT/'.laboratorio-dados3').is_file()
with tempfile.TemporaryDirectory(prefix='santafe-dados3-abi-') as tmp:
    for experimental in (False,True):
        lib=Path(tmp)/('novo.so' if experimental else 'antigo.so')
        command=['cc','-fPIC','-I'+str(ROOT/'src'),str(ROOT/'experimentos/dados-v3/ensaio-abi.c'),'-o',str(lib)]
        command+=['-bundle','-undefined','dynamic_lookup'] if platform.system()=='Darwin' else ['-shared']
        if experimental: command+=['-DSANTAFE_DADOS_EXPERIMENTAL']
        subprocess.run(command,check=True)
        source='local f,falha=módulo.carregarBib('+json.dumps(str(lib))+',"luaopen_ensaio"); '
        source+=('garanta(f,falha); garanta(f()==verdadeiro)' if experimental else 'garanta(f==nulo e falha:procure("incompat",1,verdadeiro))')
        source+='; garanta(# [nulo] == 1); mostre("ABI_OK")'
        subprocess.run([str(ROOT/'src/santafé'),'-E','-P','-e',source],check=True)
print('ABI: módulo antigo rejeitado e recompilado aceito; VM preservada: ok')
