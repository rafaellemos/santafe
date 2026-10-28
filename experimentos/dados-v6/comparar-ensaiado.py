#!/usr/bin/env python3
"""Compara todos os fontes executáveis/testes com a árvore efetivamente ensaiada."""
import hashlib, json, sys
from pathlib import Path
new, tested=(Path(x).resolve() for x in sys.argv[1:3])
assert (new/'.laboratorio-dados6').exists() and (tested/'.laboratorio-dados6').exists()
manifest=json.loads((new/'MANIFESTO-FONTES.json').read_text())
checked={}
for name in manifest:
    p=Path(name)
    covered=p.parts[0] in ('src','bibs','aplicativos','ferramentas','testes')
    covered=covered or name in ('docs/manual.html','docs/validar-manual.py','docs/API-PUBLICA-FE.tsv')
    covered=covered or name in ('experimentos/dados-v5/testar-aplicativos.py','experimentos/dados-v5/testar-instalacao.py')
    covered=covered or (p.parent.as_posix()=='experimentos/dados-v6' and p.name in
        ('aplicar.py','carga.py','operacao.py','testar-operacao.py','testar-carga-sls.py','testar-manual.py','manual.py','manual-dados.html','prism-dados6.js'))
    if not covered: continue
    a=hashlib.sha256((new/p).read_bytes()).hexdigest()
    b=hashlib.sha256((tested/p).read_bytes()).hexdigest()
    assert a==b,(name,a,b)
    checked[name]=a
print(json.dumps({'resultado':'PASSOU','arquivos':len(checked),'entrega':str(new),
                 'ensaiado':str(tested),'sha256':checked},ensure_ascii=False,indent=2))
