#!/usr/bin/env python3
"""Gera o catálogo completo de C e Fé para sublime."""
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'ferramentas'))
from catalogo_editores import catalogue

def principal():
    target = Path(__file__).resolve().parent / 'api-publica.json'
    target.write_text(json.dumps({'versão': 1, 'itens': catalogue()}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(target)

if __name__ == '__main__':
    principal()
