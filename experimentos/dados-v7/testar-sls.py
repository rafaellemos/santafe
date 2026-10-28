#!/usr/bin/env python3
from pathlib import Path
import sys,tempfile
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'testes/integracao'))
from sls.cliente import Cliente
with tempfile.TemporaryDirectory(prefix='sls-onfe7-') as tmp:
    c=Cliente([str(ROOT/'src/santafé'),'-E','-P',str(ROOT/'ferramentas/sls/sls.fé')],Path(tmp))
    try:
        c.inicie()
        for module,alias,expected in [('onfé','O',{'grave','graveAssíncrono','cod','decod','carregue'}),('arquivo','A',{'graveAtômico','graveAtômicoAssíncrono'})]:
            text='local '+alias+'=importe "'+module+'"\n'+alias+'.'
            uri=c.abra(text,module+'.fé'); c.diagnosticos(uri,1)
            items=c.solicite('textDocument/completion',c.no_ponto(uri,text,alias+'.',ultimo=True,dentro=len(alias)+1))
            labels={item['label'] for item in items}
            assert expected<=labels,(module,labels)
            print('SLS completude',module,'ok')
    finally:c.feche()
