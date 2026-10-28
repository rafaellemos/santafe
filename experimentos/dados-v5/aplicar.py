#!/usr/bin/env python3
"""Migra fronteiras comprovadas da aplicação, somente na árvore de laboratório."""
import json
from pathlib import Path
import sys

stage=Path(sys.argv[1]).resolve()
assert (stage/'.laboratorio-dados5').is_file()
report=stage/'MIGRACAO-APLICATIVOS.json'
changes=json.loads(report.read_text())
def change(name,old,new,count=1):
    p=stage/name; text=p.read_text()
    if new in text: return
    assert text.count(old)==count,(name,old,text.count(old))
    p.write_text(text.replace(old,new))
    changes.append(dict(arquivo=name,antes=old,depois=new))

change('bibs/bibf/correio/transporte.fé','local rede = importe "rede"',
       'local rede = importe "rede"\nlocal dados = importe "dados_experimentais"')
change('bibs/bibf/correio/transporte.fé',
       '    se tipo(destinatários) ~= "tabela" ou #destinatários == 0 então\n        retorne nulo, "transporte precisa de ao menos um destinatário"\n    fim',
       '    local válida, sequência = proteja(dados.lista, destinatários)\n    se não válida ou #sequência == 0 então\n        retorne nulo, "transporte precisa de ao menos um destinatário em sequência densa"\n    fim\n    destinatários = sequência')
change('bibs/bibf/correio/transporte.fé','local destinatáriosASCII = {}','local destinatáriosASCII = []')
change('bibs/bibf/correio/entrega.fé','tipo(intervalos) ~= "tabela" ou',
       '(tipo(intervalos) ~= "tabela" e tipo(intervalos) ~= "lista") ou')
change('aplicativos/carteiro/fonte/carteiro/páginas.fé','se tipo(lista) == "tabela" então',
       'se tipo(lista) == "tabela" ou tipo(lista) == "lista" então')
change('aplicativos/carteiro/fonte/carteiro/páginas.fé','tipo(participantes) ~= "tabela" ou',
       '(tipo(participantes) ~= "tabela" e tipo(participantes) ~= "lista") ou')
change('aplicativos/carteiro/fonte/carteiro/páginas.fé','se tipo(mensagens) ~= "tabela" ou mensagens.id então',
       'se tipo(mensagens) ~= "lista" e (tipo(mensagens) ~= "tabela" ou mensagens.id) então')
change('bibs/bibf/carteiro.fé','tipo(identificações) ~= "tabela" ou',
       '(tipo(identificações) ~= "tabela" e tipo(identificações) ~= "lista") ou',2)
change('experimentos/dados-v3/testar-wasm.js','WebAssembly dados.4:', 'WebAssembly dados.5:')
# Este pacote não deve acionar o fluxo estável, que recompila sem a ABI opt-in.
change('instalar.sh','#!/usr/bin/env bash\n',
       '#!/usr/bin/env bash\n# Candidato fechado para instalação operacional.\necho "Candidato dados.5: use experimentos/dados-v3/construir.sh e os testes isolados; instalação pública indisponível." >&2\nexit 2\n')
make=stage/'Makefile'
guard='$(error Candidato dados.5: use sh experimentos/dados-v3/construir.sh; instalacao publica indisponivel)\n'
if not make.read_text().startswith(guard):
    make.write_text(guard+make.read_text())
    changes.append(dict(arquivo='Makefile',antes='fluxo estável',depois=guard))
report.write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n')
print('Fronteiras dos aplicativos migradas e registradas.')
