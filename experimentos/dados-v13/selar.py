#!/usr/bin/env python3
"""Sela dados.13 somente com evidências conferidas e pendências preservadas."""
from pathlib import Path
import hashlib,json,sys,tarfile,zipfile
p=Path(sys.argv[1]).resolve()
def need(ok,why):
 if not ok:raise SystemExit(why)
def sha(b):return hashlib.sha256(b).hexdigest()
def read(path):return json.loads(path.read_text())
need(p.name=='candidato-dados-v13' and p.parent.name=='dist','destino incorreto')
need(not(p/'SHA256SUMS').exists(),'entrega já selada')
with tarfile.open(p/'santafe-candidato-dados.13-fontes.tar.gz') as t:
 ms=t.getmembers();names={m.name for m in ms}
 need(len(ms)==len(names) and all(m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in ms),'arquivo inseguro')
 manifest=json.load(t.extractfile('MANIFESTO-FONTES.json'));need(set(manifest)|{'MANIFESTO-FONTES.json'}==names,'manifesto incompleto')
 for n,h in manifest.items():need(sha(t.extractfile(n).read())==h,'fonte divergente '+n)
 need(b'"dados.13"' in t.extractfile('src/lua.h').read() and b'#define SANTAFE_ABI_MAJOR 3' in t.extractfile('src/lua.h').read(),'versão/IBA')
 for n,target in [('docs/manual.html','manual.html')]+[('experimentos/dados-v13/'+n,n) for n in ['RELATORIO.md','ESTADO.json','LEIA-ME.md']]:
  need(t.extractfile(n).read()==(p/target).read_bytes(),'documento divergente '+n)
 delta=json.load(t.extractfile('DELTA-DADOS13.json'))
 need(delta['base_sha256']=='1de126f3f0f16dbf21079f39b7f8847b03250178093c446e4e4ba25f0a2ab4e8','base divergente')
 labels=json.load(t.extractfile('experimentos/dados-v13/rotulos-publicos.json'))
for system in ['macos','debian']:
 e=p/'evidencias'/system
 for n,count in [('dados10-regressao.json',10),('dados7-regressao.json',11)]:
  r=read(e/n);need(len(r)==count and all(x['codigo']==0 for x in r) and [x['teste'] for x in r]==labels[n],system+' regressão')
 for n,count in [('iba10.json',14),('instalacao5.json',5)]:
  r=read(e/n);need(r['esperados']==len(r['passaram'])==count and r['passaram']==labels[n],system+' '+n)
 r=read(e/'operacao6.json');need(r['resultado']=='PASSOU' and len(r['testes'])==7,system+' reversão')
 need('Resumo sanitizado: ok\n' in (e/'pacotes13.log').read_text(),system+' gerenciador')
 need('ESTRUTURA_UPLOAD_OK' in (e/'estrutura13.log').read_text(),system+' imagem')
 need(read(e/'binarios13.json'),system+' hashes')
mac=read(p/'evidencias/macos/kits13.json');deb=read(p/'evidencias/debian/kits13.json')
need(mac==deb,'kits diferem entre sistemas')
for name,entries in mac.items():
 with zipfile.ZipFile(p/'editores'/name) as z:
  need(sorted(z.namelist())==sorted(entries),'kit incompleto')
  for n,h in entries.items():need(sha(z.read(n))==h,'kit difere do testado '+n)
e=p/'evidencias/debian'
for n,count in [('servicos13.json',8),('acme13.json',3),('migracao-portal13.json',4)]:
 r=read(e/n);need(r['resultado']=='PASSOU' and r['grupos']==labels[n] and len(r['grupos'])==count,n)
r=read(e/'dkim13.json');need(r['resultado']=='PASSOU' and r['originais_passaram']==r['adulteradas_recusadas']==30 and not r['conteudo_exportado'],'DKIM positivo/adulteração')
r=read(e/'dkim-expiradas13.json');need(r['assinaturas_expiradas']==r['originais_falharam']==14 and not r['relogio_alterado'],'DKIM expirado')
r=read(e/'rede-publica13.json');need(r['resultado']=='PASSOU' and len(r['grupos'])==5 and r['nucleo_e_processos_inalterados'] and r['mensagens_enviadas']==0,'rede pública')
r=read(e/'producao13.json');need(r['resultado']=='PASSOU' and r['versao']=='2.1.0' and r['http_200']==4 and r['servicos_ativos']==7,'produção')
need('18 casos + recuperação após erro: ok' in (e/'wasm13.log').read_text(),'WASM')
bins=read(e/'binarios13.json')
for n in ['santafe.js','santafe.wasm']:need(sha((p/'wasm'/n).read_bytes())==bins['src/'+n],'WASM divergente')
state=read(p/'ESTADO.json')
need(state['apto_para_homologacao'] and not state['apto_para_promocao_estavel'] and not state['producao_instalada'],'estado')
need({x['codigo'] for x in state['pendencias']}=={'MAILJET_ENTREGA','ACME_PUBLICO','PROMOCAO_INTEGRAL','PLATAFORMAS'},'pendências omitidas')
need('Não instalar em produção' in (p/'LEIA-ME.md').read_text(),'restrição ausente')
files=sorted(x for x in p.rglob('*') if x.is_file());need(not any(x.is_symlink() for x in files),'link inesperado')
(p/'SHA256SUMS').write_text(''.join(sha(x.read_bytes())+'  '+str(x.relative_to(p))+'\n' for x in files))
print('DADOS13_SELADO',len(files),'arquivos;',sum(map(len,mac.values())),'entradas de editores')
