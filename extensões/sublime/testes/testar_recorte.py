import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from realce_embutido import documentos_embutidos, recorte
from casos_concatenacoes import casos

for caso in casos():
    fonte = caso['fonte']
    documentos = documentos_embutidos(fonte)
    ponto = fonte.index(caso['trecho'])
    mapa = [par for d in documentos for par in d['mapa'] if par[0] >= 0]
    for p in range(ponto, ponto + len(caso['trecho'])):
        assert any(a <= p < b for a, b in mapa) == bool(caso['tem']), caso
    partes = [p for l in recorte(fonte)[0] for p in l['partes'] if not p.get('buraco')]
    assert all(any(p['inicio'] <= a < b <= p['fim'] for p in partes) for a,b in mapa)
grande = 'local a = [[<b title="]] ' + '.. nome .. [[x]] ' * 3000 + '.. [[fim">Oi</b>]]'
inicio = time.monotonic()
documentos = documentos_embutidos(grande)
assert len(documentos) == 1 and documentos[0]['texto'].endswith('fim">Oi</b>')
assert time.monotonic() - inicio < 5
for s in ['local a = "', 'local a = `®{', 'local a = [[<b title="x]] .. (', 'local a = ('*500]:
    documentos_embutidos(s)
print('Recorte Sublime: {} casos, isolamento, entrada incompleta e 3000 fragmentos: ok'.format(len(casos())))
