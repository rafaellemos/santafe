#!/usr/bin/env python3
"""Paletas equivalentes nos dois editores, sem alterar preferências do usuário."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
paletas = json.loads((ROOT / 'paletas.json').read_text())
for pasta in ('vscode', 'sublime'):
    (ROOT / pasta / 'paletas.json').write_text(json.dumps(paletas, indent=2) + '\n')
for tema in ('Monokai', 'Mariana', 'Celeste', 'Breakers', 'Sixteen'):
    regras = [{'scope': 'meta.santafe-embedded', 'background': '#00000001'}]
    for tipo, paleta in paletas.items():
        for nome, cor in paleta.items():
            regras.append({'scope': 'meta.santafe-soft-' + tipo + '-' + nome.lower(), 'foreground': cor, 'font_style': ''})
    regras += [
        {'scope': 'keyword.operator.interpolation.santafe, meta.interpolation.variable.santafe variable.parameter.santafe, variable.function.method.santafe',
         'foreground': '#FD971F', 'font_style': ''},
    ]
    if tema == 'Monokai':
        regras.append({'scope': 'storage.type.function.santafe', 'foreground': '#66D9EF', 'font_style': 'italic'})
    (ROOT / 'sublime/ColorSchemes' / (tema + '.sublime-color-scheme')).write_text(json.dumps({'rules': regras}, indent=2) + '\n')
