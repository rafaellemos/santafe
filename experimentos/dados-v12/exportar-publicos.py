#!/usr/bin/env python3
"""Exportação explícita de métricas: não copia registros nem textos do servidor."""
from pathlib import Path
import argparse,hashlib,json,math,re
p=argparse.ArgumentParser();p.add_argument('evidencias',type=Path);p.add_argument('destino',type=Path);a=p.parse_args()
labels=json.loads(Path(__file__).with_name('rotulos-publicos.json').read_text());out={};origins={}
def need(ok,msg):
 if not ok:raise SystemExit(msg)
def read(n):
 raw=(a.evidencias/n).read_bytes();origins[n]=hashlib.sha256(raw).hexdigest();return json.loads(raw)
def number(v):
 need(type(v) in (int,float) and math.isfinite(v) and 0<=v<10**16,'métrica inválida');return v
def metrics(v,keys):return {k:number(v[k]) for k in keys}
for n in ['dados10-regressao.json','dados7-regressao.json']:
 r=read(n);need([x['teste'] for x in r]==labels[n] and all(x['codigo']==0 for x in r),'regressão incompleta')
 out[n]=[{'teste':label,'codigo':0,'segundos':number(x['segundos'])} for label,x in zip(labels[n],r)]
for n in ['iba10.json','instalacao5.json']:
 r=read(n);need(r['passaram']==labels[n] and r['esperados']==len(labels[n]),'grupos incompletos')
 out[n]={'passaram':labels[n],'esperados':len(labels[n])}
r=read('operacao6.json');need(r['resultado']=='PASSOU' and [x['teste'] for x in r['testes']]==labels['operacao6.json'],'reversão incompleta')
out['operacao6.json']={'resultado':'PASSOU','testes':[{'teste':x} for x in labels['operacao6.json']]}
names=['src/santafé','src/santafec','src/santafe.js','src/santafe.wasm','ferramentas/sls/nativo.so','ferramentas/pacotes/nativo.so']+[f'bibs/bibc/{x}/{x}.so' for x in ['arquivo','rede','mariadb','segredo','tomada']]
r=read('binarios12.json');need(set(r)==set(names) and all(re.fullmatch('[0-9a-f]{64}',r[n]) for n in names),'hashes inválidos');out['binarios12.json']={n:r[n] for n in names}
r=read('temporarios12.json');cases=[{'caso':'compartilhado','sentinela_preservada':False,'tmpdir_conferido':True},{'caso':'isolado','sentinela_preservada':True,'tmpdir_conferido':True}]
need(r['resultado']=='PASSOU' and r['casos']==cases,'prova de temporários incompleta');out['temporarios12.json']={'resultado':'PASSOU','casos':cases}
r=read('diagnostico503.json');need(r['resultado']=='REPRODUZIDO' and r['sintetico'] is True,'diagnóstico ausente');captures=[]
for x in r['capturas']:
 need(x['http']==503 and x['errno']==2 and x['conteudo_html_exportado'] is False and re.fullmatch('[0-9a-f]{64}',x['sha256']),'captura inválida')
 captures.append({'http':503,'errno':2,'conteudo_html_exportado':False,'sha256':x['sha256'],'octetos':number(x['octetos'])})
need(0<len(captures)<=6,'capturas inválidas');out['diagnostico503.json']={'resultado':'REPRODUZIDO','sintetico':True,'capturas':captures,'ocorrencia_original_dados10_confirmada':False}
r=read('monitor12.json');need(r['resultado']=='PASSOU' and r['conteudo_privado_exportado'] is False,'monitor inválido')
out['monitor12.json']={'resultado':'PASSOU',**metrics(r,['processos_namespace','rss_namespace_kib','descritores_namespace','rss_monitor_kib','descritores_monitor','segundos_carga']),'conteudo_privado_exportado':False}
r=read('carga6.json');need(r['resultado']=='PASSOU' and r['segundos']>=600,'carga sintética incompleta')
out['carga6.json']={'resultado':'PASSOU',**metrics(r,['segundos','concorrencia','smtp_persistidas','dns_consultas','rss_pico_agregado_kib','imap_eventos_limite_persistidos','imap_conexoes_recusadas_por_protecao']),
 'latencias':{k:metrics(r['latencias'][k],['n','p50_ms','p95_ms','max_ms']) for k in ['http','imap','smtp','dns']}}
markers={'dados12-pacotes-debian.log':'ok','dados12-wasm.log':'18 casos + recuperação após erro: ok','dados12-integracao-postal-debian.log':'Correio + MariaDB + Carteiro passaram no ambiente isolado.'}
for n,marker in markers.items():
 raw=(a.evidencias/n).read_bytes();text=raw.decode('utf-8');origins[n]=hashlib.sha256(raw).hexdigest()
 need(marker in text and (n!='dados12-pacotes-debian.log' or text.strip().endswith(marker)),n+' não concluiu')
 # Texto constante. Nenhuma linha do registro é copiada.
 out[n]='Resumo sanitizado: registro completo permanece no servidor.\nSHA-256: '+origins[n]+'\n'+marker+'\n'
result={'sanitizado':True,'arquivos':out,'origens_sha256':origins,'politica':'Somente rótulos fixos, números, hashes e marcadores verificados. Sem registros brutos, mensagens, SQL, contas ou ambientes.'}
a.destino.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('EXPORTACAO_EXPLICITA_SANITIZADA',len(out),'resultados;',a.destino.stat().st_size,'octetos')
