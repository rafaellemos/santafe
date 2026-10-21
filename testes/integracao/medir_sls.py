#!/usr/bin/env python3
"""Mede o servidor real em projeto descartável; não atribui aprovação visual."""
import argparse
import json
import math
import os
from pathlib import Path
import platform
import statistics
import subprocess
import tempfile
import time
from sls.cliente import Cliente

ROOT=Path(__file__).resolve().parents[2]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--relatorio',required=True)
    args=parser.parse_args()
    measurements={}; memory={}
    def measure(name,operation,count=20):
        values=[]
        for _ in range(count):
            start=time.perf_counter(); operation(); values.append((time.perf_counter()-start)*1000)
        measurements[name]={'amostras':count,'p50_ms':round(statistics.median(values),3),
            'p95_ms':round(sorted(values)[math.ceil(count*.95)-1],3),'max_ms':round(max(values),3)}
    with tempfile.TemporaryDirectory(prefix='santafe-sls-carga-') as temporary:
        root=Path(temporary).resolve()
        for i in range(100):
            (root/f'modulo{i:03}.fé').write_text('local M={}\n'+''.join(
                f'função M.item{j}(a,b) retorne a+b fim\n' for j in range(30))+'retorne M\n')
        source='local M=importe "modulo000"\n'+''.join(
            f'início local valor{i}={i}; mostre(`®valor{i}`) fim\n' for i in range(1500))
        c=Cliente([str(ROOT/'src/santafé'),str(ROOT/'ferramentas/sls/sls.fé')],root,prazo=20)
        def rss():
            try:
                return int(subprocess.check_output(['ps','-o','rss=','-p',str(c.processo.pid)],text=True).strip())
            except (OSError,ValueError,subprocess.CalledProcessError): return None
        try:
            c.inicie(); memory['inicial_kib']=rss()
            uri=c.abra(source)
            assert c.diagnosticos(uri,1)==[]
            measure('simbolos_documento_1500_linhas',lambda:c.solicite('textDocument/documentSymbol',{'textDocument':{'uri':uri}}))
            measure('hover',lambda:c.solicite('textDocument/hover',c.no_ponto(uri,source,'valor500')))
            measure('tokens_semanticos',lambda:c.solicite('textDocument/semanticTokens/full',{'textDocument':{'uri':uri}}))
            measure('simbolos_projeto_100_modulos',lambda:c.solicite('workspace/symbol',{'query':'item'}),10)
            memory['indice_aquecido_kib']=rss()
            version=1
            def change():
                nonlocal version
                version+=1
                c.mude(uri,source+'\n-- versão '+str(version))
                assert c.diagnosticos(uri,version)==[]
            measure('edicao_e_diagnostico_1500_linhas',change)
            for cycle in range(4):
                for i in range(12):
                    text='local função f(a) retorne a fim\n'*500
                    # Reabrir o mesmo conjunto: novos nomes a cada ciclo
                    # aumentariam legitimamente o índice de arquivos fechados.
                    u=c.abra(text,f'carga{i}.fé')
                    c.solicite('textDocument/documentSymbol',{'textDocument':{'uri':u}})
                    c.notifique('textDocument/didClose',{'textDocument':{'uri':u}})
                c.solicite('workspace/symbol',{'query':'não-existe'})
                memory[f'apos_ciclo_{cycle+1}_kib']=rss()
            c.notifique('textDocument/didClose',{'textDocument':{'uri':uri}})
            c.solicite('workspace/symbol',{'query':'não-existe'})
            memory['apos_fechar_kib']=rss()
            info=c.informacao
        finally: c.feche()
        values=[v for v in memory.values() if v is not None]
        # Envelope de regressão conservador, não promessa de latência universal.
        assert not values or max(values)<512*1024, memory
        if memory['apos_ciclo_3_kib'] is not None and memory['apos_ciclo_4_kib'] is not None:
            assert memory['apos_ciclo_4_kib']-memory['apos_ciclo_3_kib']<50*1024,memory
        assert all(v['p95_ms']<2500 for v in measurements.values()),measurements
        result={'sls':info,'sistema':platform.platform(),'cpu':platform.processor(),
            'cpus_logicas':os.cpu_count(),'projeto':{'modulos':100,'funcoes_por_modulo':30,
            'linhas_documento':1501,'octetos_documento':len(source.encode())},
            'medicoes':measurements,'memoria_rss':memory,'resultado':'ok',
            'limites':'RSS inclui alocador do processo; não é prova de ausência de vazamentos.'}
        Path(args.relatorio).write_text(json.dumps(result,ensure_ascii=False,indent=2))
        print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
