#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
source=(ROOT/'experimentos/dados-v5/empacotar.py').read_text()
source=source.replace("assert (stage/'.laboratorio-dados5').is_file()", "assert (stage/'.laboratorio-dados8').is_file()")
source=source.replace("'MIGRACAO.json',", "'.laboratorio-dados6','.laboratorio-dados7','.laboratorio-dados8','MIGRACAO-COLARES8.json','MIGRACAO.json',")
# O WASM Oniguruma é dependência vendorizada dos testes TextMate, não núcleo.
source=source.replace("if p.suffix in {", "if p.name != 'onig.wasm' and p.suffix in {")
exec(compile(source,str(ROOT/'experimentos/dados-v5/empacotar.py'),'exec'))
