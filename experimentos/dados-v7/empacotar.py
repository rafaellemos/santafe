#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
source=(ROOT/'experimentos/dados-v5/empacotar.py').read_text()
source=source.replace("assert (stage/'.laboratorio-dados5').is_file()", "assert (stage/'.laboratorio-dados7').is_file()")
source=source.replace("'MIGRACAO.json',", "'.laboratorio-dados6','.laboratorio-dados7','MIGRACAO.json',")
exec(compile(source,str(ROOT/'experimentos/dados-v5/empacotar.py'),'exec'))
