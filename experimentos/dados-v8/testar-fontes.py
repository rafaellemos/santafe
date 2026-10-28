#!/usr/bin/env python3
"""Compilação de toda a árvore de fontes Fé do candidato, sem execução."""
from pathlib import Path
import json,subprocess
ROOT=Path(__file__).resolve().parents[2]
passed=[]
for folder in ('bibs','ferramentas','aplicativos','exemplos','testes'):
    for p in sorted((ROOT/folder).rglob('*.fé')):
        result=subprocess.run([str(ROOT/'src/santafec'),'-p',str(p)],capture_output=True,text=True,timeout=15)
        assert result.returncode==0,(str(p),result.stderr)
        passed.append(str(p.relative_to(ROOT)))
(ROOT/'evidencias/dados8-fontes.json').write_text(json.dumps(passed,ensure_ascii=False,indent=2)+'\n')
print('FONTES_FÉ_COMPILADAS',len(passed))
