"""Ensaios automáticos em Windows11 ARM; pacote x64 em emulação, sem GUI."""
from pathlib import Path,PurePosixPath
import ctypes,hashlib,json,os,platform,subprocess,sys,tempfile,traceback,uuid,zipfile
sys.stdout.reconfigure(encoding='utf-8',errors='backslashreplace')
here=Path(__file__).resolve().parent
out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
result={'candidato':'dados.20','resultado':'em_execucao','testes':[],
        'producao_alterada':False,'validacao_visual':False,'execucao_x64_emulada':True}
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ok(name):result['testes'].append({'nome':name,'passou':True});print('OK',name,flush=True)
def execute(name,args,env=None,cwd=None):
 p=subprocess.run([str(a) for a in args],capture_output=True,env=env,cwd=cwd,timeout=240)
 (out/(name+'.log')).write_bytes(p.stdout+b'\nSTDERR\n'+p.stderr)
 assert p.returncode==0,(name,p.returncode,p.stderr[-1000:]);ok(name)
def install(name,args):
 execute(name,[Path(os.environ['SystemRoot'])/'System32/msiexec.exe',*args,'/qn','/norestart','/l*v',out/(name+'-msi.log')])
def verify(meta,target,name):
 for n,h in meta['arquivos'].items():assert digest(target/n)==h,n
 ok(name)
metas=[];installed=[]
try:
 v=sys.getwindowsversion();info=ctypes.create_string_buffer(64);ctypes.windll.kernel32.GetNativeSystemInfo(info)
 arch=int.from_bytes(info.raw[:2],'little')
 assert v.product_type==1 and v.build>=22000 and arch==12,(v,arch)
 result['sistema']={'versao':platform.platform(),'build':v.build,'product_type':v.product_type,'arquitetura_nativa':'ARM64','python':platform.machine()}
 entry=out/'entrada';entry.mkdir()
 with zipfile.ZipFile(sys.argv[1]) as z:
  names=z.namelist();assert len(names)==len(set(names))
  for n in names:
   p=PurePosixPath(n);assert not p.is_absolute() and '..' not in p.parts and '\\' not in n and ':' not in n
  z.extractall(entry)
 for n,h in json.loads((entry/'MANIFESTO.json').read_text(encoding='utf-8')).items():assert digest(entry/n)==h,n
 old=json.loads((here/'base/dados19.json').read_text(encoding='utf-8'));new=json.loads((entry/'dados20.json').read_text(encoding='utf-8'));metas=[old,new]
 assert digest(here/'base/dados19.msi')=='5f739b13ec504117b11adf1236b9426c1c6091e9a5c86a8f4df5fa2caed80df2'
 assert digest(entry/'dados20.msi')==new['sha256'];ok('entrada-e-msi-conferidos')
 target=Path(os.environ['LOCALAPPDATA'])/'Programs'/('Santafe-Windows11-'+uuid.uuid4().hex[:10])
 install('instalar-candidato19',['/i',here/'base/dados19.msi','INSTALLDIR='+str(target)]);installed.append(old)
 verify(old,target,'candidato19-integro')
 install('atualizar19-para20',['/i',entry/'dados20.msi']);installed=[new];verify(new,target,'candidato20-integro')
 from licencas import verify_tree
 assert verify_tree(target)==6;ok('seis-avisos-instalados')
 from dependencias import verify_package
 assert verify_package(lambda n:(target/n).read_bytes())==4;ok('fontes-e-dependencias-instaladas')
 env={k:v for k,v in os.environ.items() if k.upper() in ('SYSTEMROOT','WINDIR','TEMP','TMP','USERPROFILE')};env['PATH']=str(Path(os.environ['SystemRoot'])/'System32')
 work=out/'projeto-ação';work.mkdir()
 execute('versao-x64-no-windows11',[target/'bin/santafe.exe','-v'],env,work)
 execute('contrato-listas-nulos',[target/'bin/santafe.exe',entry/'source/listas.fé'],env,work)
 execute('contrato-onfe',[target/'bin/santafe.exe',entry/'source/onfe.fé'],env,entry/'source')
 execute('sls39-windows11',[sys.executable,here/'portatil_sls.py',entry/'source',target/'bin/santafe-sls.exe',out/'sls-windows11.json'],env)
 execute('instalar-biblioteca-fe',[target/'bin/santafe.exe','instale','exemplo','1.0.0','--repositorio-local',entry/'repo'],env,work)
 execute('importar-biblioteca-fe',[target/'bin/santafe.exe','-e','garanta((importe "exemplo").valor==42)'],env,work)
 (target/'share/santafé/1.0/ferramentas/sls/nativo.dll').unlink()
 install('reparar20',['/fa',entry/'dados20.msi']);verify(new,target,'reparacao-integra')
 install('remover20',['/x',new['product_code']]);installed=[]
 assert not (target/'bin/santafe.exe').exists() and (work/'santafe.lock').is_file();ok('remocao-preservou-projeto')
 install('reversao-explicita-para19',['/i',here/'base/dados19.msi','INSTALLDIR='+str(target)]);installed=[old];verify(old,target,'reversao19-integra')
 install('remover19',['/x',old['product_code']]);installed=[]
 result['resultado']='passou_windows11_arm_pacote_x64'
except BaseException as e:
 result['resultado']='falhou';result['falha']=str(e);result['rastro']=traceback.format_exc();traceback.print_exc()
finally:
 for m in installed:
  try:install('limpeza-'+m['versao_msi'],['/x',m['product_code']])
  except Exception:result['limpeza_pendente']=True
 (out/'resultado.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
sys.exit(0 if result['resultado'].startswith('passou') else 1)
