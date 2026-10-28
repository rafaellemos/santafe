#!/usr/bin/env python3
"""Selagem condicionada a evidências completas; nunca instala produção."""
from pathlib import Path
import hashlib,json,sys,tarfile,zipfile
p=Path(sys.argv[1]).resolve()
def need(ok,why):
 if not ok:raise SystemExit(why)
need(p.name=='candidato-dados-v12' and p.parent.name=='dist','destino incorreto');need(not(p/'SHA256SUMS').exists(),'entrega já selada')
with tarfile.open(p/'santafe-candidato-dados.12-fontes.tar.gz') as t:
 ms=t.getmembers();names={x.name for x in ms}
 need(len(ms)==len(names) and all(x.isfile() and not Path(x.name).is_absolute() and '..' not in Path(x.name).parts for x in ms),'arquivo inseguro')
 manifest=json.load(t.extractfile('MANIFESTO-FONTES.json'));need(set(manifest)|{'MANIFESTO-FONTES.json'}==names,'manifesto incompleto')
 for n,h in manifest.items():need(hashlib.sha256(t.extractfile(n).read()).hexdigest()==h,'fonte divergente '+n)
 need(b'"dados.12"' in t.extractfile('src/lua.h').read(),'versão')
 need(b'#define SANTAFE_ABI_MAJOR 3' in t.extractfile('src/lua.h').read(),'IBA')
 for n,target in [('docs/manual.html','manual.html')]+[('experimentos/dados-v12/'+n,n) for n in ['RELATORIO.md','ESTADO.json','LEIA-ME.md']]:need(t.extractfile(n).read()==(p/target).read_bytes(),'documento divergente '+n)
for system in ['macos','debian']:
 e=p/'evidencias'/system
 for n,count in [('dados10-regressao.json',10),('dados7-regressao.json',11)]:
  r=json.loads((e/n).read_text());need(len(r)==count and all(x['codigo']==0 for x in r),system+' regressão')
 for n,count in [('iba10.json',14),('instalacao5.json',5)]:
  r=json.loads((e/n).read_text());need(r['esperados']==len(r['passaram'])==count,system+' '+n)
 r=json.loads((e/'operacao6.json').read_text());need(r['resultado']=='PASSOU' and len(r['testes'])==7,system+' reversão')
 need((e/('dados12-pacotes-'+system+'.log')).read_text().strip().endswith('ok'),system+' gerenciador')
 need(json.loads((e/'binarios12.json').read_text()),system+' binários')
 need('Correio + MariaDB + Carteiro passaram no ambiente isolado.' in (e/('dados12-integracao-postal-'+system+'.log')).read_text(),system+' integração postal')
e=p/'evidencias/debian';r=json.loads((e/'temporarios12.json').read_text())
need(r['resultado']=='PASSOU' and [x['sentinela_preservada'] for x in r['casos']]==[False,True],'prova de temporários')
r=json.loads((e/'diagnostico503.json').read_text())
need(r['resultado']=='REPRODUZIDO' and r['sintetico'] and r['capturas'],'reprodução HTTP ausente')
need(all(x['http']==503 and x['errno']==2 and not x['conteudo_html_exportado'] for x in r['capturas']),'diagnóstico HTTP divergente')
r=json.loads((e/'editores12.json').read_text());need(r['resultado']=='PASSOU' and r['pacotes']==2 and r['entradas']==47,'conteúdo dos editores divergente')
r=json.loads((e/'monitor12.json').read_text());need(r['resultado']=='PASSOU' and r['processos_namespace']>=11,'monitor incompleto')
r=json.loads((e/'carga6.json').read_text());need(r['resultado']=='PASSOU' and r['segundos']>=600,'carga sintética corrigida')
r=json.loads((e/'replica12-real.json').read_text());c=r['carga'];need(r['resultado']=='PASSOU' and r['sanitizado'] and len(r['grupos'])==12 and c['resultado']=='PASSOU' and c['segundos']>=3600,'carga prolongada incompleta')
need(len(c['amostras'])>=600 and len(c['contadores'])==6,'amostragem insuficiente')
need(all(isinstance(x,int) and x>0 for x in c['contadores']),'leitor sem operações')
need(c['amostras'][0]['s']<10 and c['amostras'][-1]['s']>=3600,'janela de observação incompleta')
need(all(0<=b['s']-a['s']<=15 and b['operacoes']>=a['operacoes'] for a,b in zip(c['amostras'],c['amostras'][1:])),'lacuna no monitoramento')
need(sum(c['contadores'])==c['amostras'][-1]['operacoes'],'contadores divergentes')
need(c['limite_pedidos_por_segundo']==12,'limite de tráfego divergente')
for x in c['amostras']:
 need(0<x['rss_kib']<=800*1024 and x['livre_mib']>=2048 and x['registros_bytes']<=128*1024**2 and 0<x['descritores']<=2048 and x['memoria_disponivel_kib']>=768*1024,'orçamento de carga')
reads=[x for x in r['grupos'] if 'conteúdo integral' in x['grupo']]
need(len(reads)==3 and reads[1]['originais']==reads[2]['originais']>reads[0]['originais'] and reads[1]['anexos']==reads[2]['anexos']>reads[0]['anexos'],'reversão perdeu novas escritas')
r=json.loads((e/'producao12.json').read_text());need(r['resultado']=='PASSOU' and r['nucleo_inalterado'] and r['mesmos_processos_e_instantes_de_inicio'] and r['servicos_ativos']==7 and r['http_200']==4 and r['versao']=='2.1.0','produção divergente')
need('18 casos + recuperação após erro: ok' in (e/'dados12-wasm.log').read_text(),'WASM')
b=json.loads((e/'binarios12.json').read_text())
for n in ['santafe.js','santafe.wasm']:need(hashlib.sha256((p/'wasm'/n).read_bytes()).hexdigest()==b['src/'+n],'WASM divergente')
with zipfile.ZipFile(p/'editores/santafe-dados-experimental-0.0.12.vsix') as z:need(json.loads(z.read('extension/package.json'))['version']=='0.0.12','VS Code')
with zipfile.ZipFile(p/'editores/SantafeDados.sublime-package') as z:need(b'0.0.12' in z.read('README.md'),'Sublime')
state=json.loads((p/'ESTADO.json').read_text());need(state['apto_para_homologacao'] and not state['apto_para_promocao_estavel'] and not state['producao_instalada'],'estado')
need('Não instalar em produção' in (p/'LEIA-ME.md').read_text(),'restrição ausente')
files=sorted(x for x in p.rglob('*') if x.is_file());need(not any(x.is_symlink() for x in files),'link inesperado')
(p/'SHA256SUMS').write_text(''.join(hashlib.sha256(x.read_bytes()).hexdigest()+'  '+str(x.relative_to(p))+'\n' for x in files))
print('DADOS12_SELADO',len(files),'arquivos')
