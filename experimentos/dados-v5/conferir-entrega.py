#!/usr/bin/env python3
"""Confere fontes entregues contra árvore ensaiada; diferenças só de registro."""
import hashlib
import json
from pathlib import Path
import sys

delivery=Path(sys.argv[1]).resolve(); tested=Path(sys.argv[2]).resolve()
manifest=json.loads((delivery/'MANIFESTO-FONTES.json').read_text())
allowed={'MIGRACAO-APLICATIVOS.json','experimentos/dados-v5/PLANO.md',
 'experimentos/dados-v5/LEIA-ME.md','experimentos/dados-v5/RELATORIO.md',
 'experimentos/dados-v5/preparar.py','experimentos/dados-v5/empacotar.py',
 'experimentos/dados-v5/conferir-entrega.py'}
same=0; changes=[]
for name,expected in manifest.items():
    assert hashlib.sha256((delivery/name).read_bytes()).hexdigest()==expected,name
    previous=tested/name
    if previous.is_file() and hashlib.sha256(previous.read_bytes()).hexdigest()==expected:
        same+=1
    else:
        assert name in allowed, 'implementação/teste diferente da árvore ensaiada: '+name
        changes.append(name)
print(json.dumps({'iguais':same,'diferencas_de_registro':changes,'total':len(manifest)},ensure_ascii=False,indent=2))
