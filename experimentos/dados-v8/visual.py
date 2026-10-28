#!/usr/bin/env python3
"""Espelho visual do manual candidato em loopback; ativos públicos só de leitura.

Não é publicação. O WASM é copiado da compilação candidata, nunca do portal.
"""
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[2]
out=ROOT/'evidencias/visual'; out.mkdir(parents=True,exist_ok=True)
t=(ROOT/'docs/manual.html').read_text()
for attr in ('href','src'):
    t=t.replace(attr+'="/estático/',attr+'="https://xn--santaf-gva.dev.br/estático/')
t=t.replace('https://xn--santaf-gva.dev.br/estático/wasm/candidato-dados.9/','/estático/wasm/candidato-dados.9/')
t=t.replace('https://xn--santaf-gva.dev.br/estático/js/prism-dados8.js','/prism-dados8.js')
(out/'manual.html').write_text(t)
shutil.copy2(ROOT/'experimentos/dados-v8/prism-dados8.js',out/'prism-dados8.js')
wasm=out/'estático/wasm/candidato-dados.9'; wasm.mkdir(parents=True,exist_ok=True)
for name in ('santafe.js','santafe.wasm'):
    shutil.copy2(ROOT/'src'/name,wasm/name)
print(out)
