#!/usr/bin/env python3
"""Exporta somente contagens; nenhum conteúdo postal, SQL ou segredo."""
from pathlib import Path
import argparse,json,math
p=argparse.ArgumentParser();p.add_argument('laboratorio',type=Path);p.add_argument('destino',type=Path);a=p.parse_args()
r=json.loads((a.laboratorio/'resultado-dados12.json').read_text());c=json.loads((a.laboratorio/'carga-dados12.json').read_text())
assert r['resultado']=='PASSOU' and c['resultado']=='PASSOU' and c['segundos']>=3600
allowed={'grupo','santafe_comunidade','paodocafe','sls','iba','requisicoes','zonas','respostas_assinadas','originais','anexos','paginas','entrada_sem_destino_http','segundos','operacoes','clientes','p95_ms','rss_max_kib','disco_livre_min_mib','fase'}
labels=['réplica reutilizada sem duplicação de bancos e depósitos',
 'SLS, CLI e SDK da geração candidata instalados no chroot',
 'candidata: nginx capturado, TLS de teste e proxy dos dois domínios',
 'candidata: zonas DNS reais em UDP/TCP e chaves DNSSEC preservadas',
 'candidata: leitura dos aplicativos e conteúdo integral',
 'carga prolongada da réplica',
 'candidata: SMTP TLS, filas, compositor, login e IMAP nos dois bancos',
 'candidata: leitura dos aplicativos e conteúdo integral',
 'estavel: nginx capturado, TLS de teste e proxy dos dois domínios',
 'estavel: zonas DNS reais em UDP/TCP e chaves DNSSEC preservadas',
 'estavel: leitura dos aplicativos e conteúdo integral',
 'reversão preservou novas escritas após carga prolongada']
assert [x['grupo'] for x in r['grupos']]==labels
groups=[]
for label,x in zip(labels,r['grupos']):
 row={'grupo':label}
 for k in sorted(allowed-{'grupo'}):
  if k not in x:continue
  if k in {'sls','fase'}:
   expected={'sls':'1.0.0-dados.12','fase':'dados12-depois'}[k]
   assert x[k]==expected;row[k]=expected
  else:
   assert type(x[k]) in (int,float) and math.isfinite(x[k]) and 0<=x[k]<10**16
   row[k]=x[k]
 groups.append(row)
samplekeys={'s','livre_mib','rss_kib','memoria_disponivel_kib','descritores','registros_bytes','operacoes'}
samples=[{k:v for k,v in x.items() if k in samplekeys} for x in c['amostras']]
assert all(all(type(v) in (int,float) and math.isfinite(v) and 0<=v<10**16 for v in x.values()) for x in samples)
assert len(c['contadores'])==6 and all(type(v)==int and v>0 for v in c['contadores'])
assert c['limite_pedidos_por_segundo']==12 and type(c['segundos']) in (int,float) and 3600<=c['segundos']<7500
report={'resultado':'PASSOU','sanitizado':True,'grupos':groups,'carga':{'resultado':'PASSOU','segundos':c['segundos'],'contadores':c['contadores'],'amostras':samples,'limite_pedidos_por_segundo':c['limite_pedidos_por_segundo']},'limites':['Uma hora de leitura HTTP; SMTP/IMAP e novas escritas conferidos depois','TLS de teste; sem relay externo, antimalware, upload de comunidade ou renovação pública','Réplica reutilizada, sem cópia adicional de bancos/depósitos']}
a.destino.parent.mkdir(parents=True,exist_ok=True);a.destino.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('EVIDENCIA_SANITIZADA',len(groups),'grupos;',sum(c['contadores']),'pedidos')
