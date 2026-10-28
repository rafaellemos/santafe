#!/usr/bin/env python3
"""Correções do candidato encontradas na carga, com substituição conferida."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
assert (ROOT/'.laboratorio-dados6').exists()
p=ROOT/'bibs/bibf/correio/imap.fé'; text=p.read_text()
old='se sessão.fechada ou sessão.enviando então retorne fim\n        local item = tabela.remova(sessão.saídas, 1)'
new='se sessão.fechada ou sessão.enviando ou #sessão.saídas == 0 então retorne fim\n        local item = tabela.remova(sessão.saídas, 1)'
if new not in text:
    assert text.count(old)==1
    p.write_text(text.replace(old,new))
