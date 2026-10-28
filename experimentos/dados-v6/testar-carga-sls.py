#!/usr/bin/env python3
import json, os, statistics, subprocess, sys, tempfile, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'testes/integracao'))
from sls.cliente import Cliente
with tempfile.TemporaryDirectory(prefix='sls-carga6-') as tmp:
    client=Cliente(['/bin/sh',str(ROOT/'experimentos/dados-v3/santafe-sls-dados')],Path(tmp),prazo=15)
    lat=[]
    try:
        client.inicie()
        code='local itens=[nulo,"José"]\n'+'itens[1]=nulo\n'*1500
        uri=client.abra(code,'carga.fé'); diagnostics=client.diagnosticos(uri); assert not diagnostics,diagnostics
        for version in range(2,202):
            start=time.monotonic()
            start_column=code.index('José')
            client.notifique('textDocument/didChange',{'textDocument':{'uri':uri,'version':version},'contentChanges':[{'range':{'start':{'line':0,'character':start_column},'end':{'line':0,'character':start_column+4}},'text':'José' if version%2==0 else 'João'}]})
            diagnostics=client.diagnosticos(uri,version); assert not diagnostics,(version,diagnostics)
            lat.append(time.monotonic()-start)
    finally: client.feche()
    s=sorted(lat)
    result={'resultado':'PASSOU','mudancas_incrementais':len(s),'linhas':1502,'p50_ms':round(statistics.median(s)*1000,2),'p95_ms':round(s[int(len(s)*.95)-1]*1000,2),'max_ms':round(max(s)*1000,2),'limite_por_resposta_s':15}
    (ROOT/'evidencias/carga-sls6.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
