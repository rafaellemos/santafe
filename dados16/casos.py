"""Adversarial Windows integration. Real packages, handles, job objects and LSP."""
from pathlib import Path
import json,os,subprocess,sys,time,threading,ssl,functools,ctypes

def test(root,out,run,sf,exe,init,lit):
 sys.path.insert(0,str(root/'testes/integracao'))
 from sls.cliente import Cliente
 work=out/'casos';work.mkdir();repo=work/'repo';repo.mkdir();a=work/'projeto-A';a.mkdir();b=work/'projeto-B';b.mkdir()
 def cli(name,wd,*args,ok=True,env=None):return run(name,[exe,*args],wd,0 if ok else None,env=env)
 toolpath=root/'ferramentas'
 setup='módulo.caminho='+lit(str(toolpath/'?.fé').replace('\\','/'))+'..";"..módulo.caminho; '+init+'local F=(importe "pacotes.formatos")(N);local C=(importe "pacotes.cliente")(N,F); '
 def fixture(name,version,value,native=False):
  src=work/(name+'-'+version);src.mkdir();(src/'bibf').mkdir()
  files={'README.md':'# Exemplo','LICENSE':'MIT','bibf/exemplo.fé':f'local M={{valor={value}}}; função M.somar(a,b) retorne a+b fim; retorne M'}
  data={'formato':1,'nome':name,'versao':version,'descricao':'Ensaio isolado','licenca':'MIT','autores':['Homologação'],'fonte':'https://example.invalid/fonte','modulos':{'exemplo':'bibf/exemplo.fé'}}
  if native:
   (src/'src').mkdir();files['src/soma.c']='#include "lua.h"\n#include "lauxlib.h"\nSANTAFE_MODULE_ABI;\nstatic int sum(lua_State*L){lua_pushinteger(L,luaL_checkinteger(L,1)+luaL_checkinteger(L,2));return 1;}\nint luaopen_soma(lua_State*L){lua_pushcfunction(L,sum);return 1;}'
   data['nativos']={'soma':{'fontes':['src/soma.c']}}
  data['arquivos']=list(files)
  for p,s in files.items():(src/p).write_text(s,encoding='utf-8')
  (src/'santafe.json').write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
  return src
 src=fixture('exemplo','1.0.0',42);pkg=work/'a.sfp'
 cli('empacotar',work,'empacote',src,pkg);cli('catalogar',work,'catalogo',repo,pkg)
 cli('instalar-fe',a,'instale','exemplo','1.0.0','--repositorio-local',repo)
 cli('importar-fe',a,'-e','garanta((importe "exemplo").valor==42)')
 lock=(a/'santafe.lock').read_bytes()
 cli('instalar-travado',a,'instale','--travado','--repositorio-local',repo);assert lock==(a/'santafe.lock').read_bytes()
 offline=work/'repositorio-desligado';repo.rename(offline)
 cli('instalar-offline',a,'instale','--sem-rede','--repositorio-local',repo);offline.rename(repo)
 state=json.loads((a/'.santafe/estado.json').read_text());source=a/'.santafe/geracoes'/state['geracao']/'pacotes/exemplo/bibf/exemplo.fé'
 original=source.read_bytes();source.write_text('retorne {valor=-1}',encoding='utf-8')
 cli('recusar-importacao-adulterada',a,'-e','importe "exemplo"',ok=False);source.write_bytes(original)
 newer=fixture('exemplo','1.1.0',99);pkg2=work/'b.sfp';cli('empacotar-atualizacao',work,'empacote',newer,pkg2);cli('catalogar-atualizacao',work,'catalogo',repo,pkg2)
 cli('segundo-projeto',b,'instale','exemplo','1.1.0','--repositorio-local',repo);cli('segundo-projeto-isolado',b,'-e','garanta((importe "exemplo").valor==99)');cli('primeiro-projeto-isolado',a,'-e','garanta((importe "exemplo").valor==42)')
 for phase in ('verificado','preparado','transacao','manifesto','lock','confirmado'):
  p=work/('recuperacao-'+phase);p.mkdir();cli('preparar-'+phase,p,'instale','exemplo','1.0.0','--repositorio-local',repo)
  sf('interromper-'+phase,setup+f'garanta(C.instale({lit(p)},"exemplo","1.1.0",{{repositórioLocal={lit(repo)},observador=função(f) se f=="{phase}" então erro("interrupção") fim fim}}))',expected=None)
  value=99 if phase=='confirmado' else 42
  cli('execucao-antes-recuperar-'+phase,p,'-e',f'garanta((importe "exemplo").valor=={value})')
  sf('recuperar-'+phase,setup+f'local r=garanta(N.raiz({lit(p)}));garanta(r:trave());C.recupere(r);r:feche()')
  cli('execucao-depois-recuperar-'+phase,p,'-e',f'garanta((importe "exemplo").valor=={value})');assert not (p/'.santafe/transacao.json').exists()
 damaged=json.loads(lock);damaged['dependencias']['exemplo']='9.0.0';(a/'santafe.lock').write_text(json.dumps(damaged),encoding='utf-8')
 cli('recusar-lock-alterado',a,'instale','--travado','--repositorio-local',repo,ok=False);(a/'santafe.lock').write_bytes(lock)
 cache=next((a/'.santafe/cache').glob('*.sfp'));original=cache.read_bytes();cache.write_bytes(b'bad')
 cli('recusar-cache-alterado',a,'instale','--sem-rede','--repositorio-local',repo,ok=False);cache.write_bytes(original)
 # Real installed-source resolution and no dependency execution by the SLS.
 c=Cliente([str(root/'src/santafe-sls.exe')],a,prazo=15)
 try:
  c.inicie();text='local E=importe "exemplo"; mostre(E.somar(1,2))';uri=c.abra(text)
  where=c.no_ponto(uri,text,'somar',dentro=1);location=c.solicite('textDocument/definition',where)
  assert location and '/.santafe/geracoes/' in location['uri'],location
  assert 'error' in c.solicite_bruto('textDocument/rename',{**where,'newName':'novo'})
 finally:c.feche()
 sf('sls-pacote-confirmado','mostre("resolução e recusa de rename conferidas pelo cliente independente")')
 for i,path in enumerate(('../fora','/fora','a/../b','x\\y','a//b','a/.','a.','a ','NUL','CON.txt','COM1','LPT9.log','arquivo:ads','x?y','\\\\server\\share','C:relativo')):
  sf('caminho-recusa-'+str(i),init+'N.chaveCaminho('+lit(path)+')',expected=None)
 sf('colisao-unicode',init+'garanta(N.chaveCaminho("José")==N.chaveCaminho("JOSÉ"))')
 outside=work/'outside';outside.mkdir();secret=outside/'secret';secret.write_text('INTACTO',encoding='utf-8')
 junction=a/'junction';subprocess.run(['cmd.exe','/d','/c','mklink','/J',str(junction),str(outside)],check=True,capture_output=True)
 sf('recusar-juncao-leitura',init+f'local r=garanta(N.raiz({lit(a)}));garanta(r:leia("junction/secret"))',expected=None)
 sf('recusar-juncao-escrita',init+f'local r=garanta(N.raiz({lit(a)}));garanta(r:grave("junction/secret","ERRO",verdadeiro))',expected=None)
 sf('recusar-raiz-juncao',init+f'garanta(N.raiz({lit(junction)}))',expected=None)
 os.link(secret,a/'hardlink')
 sf('recusar-hardlink',init+f'local r=garanta(N.raiz({lit(a)}));garanta(r:leia("hardlink"))',expected=None)
 assert secret.read_text()=='INTACTO'
 sf('recusar-trava-dupla',init+f'local a=garanta(N.raiz({lit(a)}));local b=garanta(N.raiz({lit(a)}));garanta(a:trave());garanta(b:trave())',expected=None)
 # File size limit, invalid base64 and corrupt metadata.
 sf('limite-leitura',init+f'local r=garanta(N.raiz({lit(a)}));garanta(r:grave("grande","12345",falso));garanta(r:leia("grande",4))',expected=None)
 sf('base64-nao-canonico',init+'N.decodBase64("Zh==")',expected=None)
 # Actual native package: permission required, trusted absolute compiler.
 native=fixture('nativo','1.0.0',7,True);np=work/'native';np.mkdir();nativepkg=work/'native.sfp'
 cli('empacotar-c',work,'empacote',native,nativepkg);cli('catalogar-c',work,'catalogo',repo,nativepkg)
 cli('recusar-c-sem-permissao',np,'instale','nativo','*','--repositorio-local',repo,ok=False)
 cli('instalar-c-autorizado',np,'instale','nativo','*','--repositorio-local',repo,'--permitir-nativo')
 cli('importar-c',np,'-e','garanta((importe "soma")(20,22)==42)')
 probe=out/'sonda.exe';run('compilar-sonda-processos',['gcc',Path(__file__).parent/'sonda-processo.c','-o',probe])
 def execute(name,args,limit=2,maxout=4096,assertion='c==0',env=None):
  return sf(name,init+f'local r=garanta(N.raiz({lit(a)}));local c,s=r:execute({{'+','.join(lit(x) for x in [probe,*args])+f'}},{limit},{maxout});garanta({assertion},s)',env=env)
 execute('argumentos-sem-shell',['args','$(touch NEVER)','a b','x"y','fim\\'],assertion='c==0 e s=="$(touch NEVER)\\na b\\nx\\\"y\\nfim\\\\\\n"')
 env=os.environ.copy();env['SANTAFE_TEST_SECRET']='NAO_HERDAR'
 execute('ambiente-sem-segredos',['env'],assertion='c==0 e s=="LIMPO"',env=env)
 execute('prazo-processo',['sleep'],limit=1,assertion='c==124')
 execute('limite-saida',['flood'],assertion='c==125')
 execute('arvore-encerrada',['tree'])
 execute('arvore-prazo',['treehold'],limit=1,assertion='c==124')
 time.sleep(2.5);assert not (a/'descendente-vazou').exists()
 sf('descendentes-conferidos','mostre("árvore encerrada e marcador externo ausente")')
