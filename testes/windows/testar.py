"""Windows native tools, on top of the already-built candidate. No deployment."""
from pathlib import Path
import json,os,subprocess,sys,time,shutil,traceback
from recursos import compile_resource
HERE=Path(__file__).resolve().parent
ROOT=Path(sys.argv[1]).resolve();OUT=Path(sys.argv[2]).resolve();OUT.mkdir(exist_ok=True)
assert sys.platform=='win32'
sys.stdout.reconfigure(encoding='utf-8',errors='backslashreplace')
RESULT={'distribuicao':'3.0.0','testes':[],'producao_alterada':False,'resultado':'em_execucao'}
def save(): (OUT/'resultado.json').write_text(json.dumps(RESULT,ensure_ascii=False,indent=2),encoding='utf-8')
def run(name,cmd,cwd=ROOT,expected=0,stdin=None,timeout=90,env=None):
 t=time.monotonic();p=subprocess.run([str(x) for x in cmd],cwd=cwd,input=stdin,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout,env=env)
 (OUT/(name+'.log')).write_bytes(p.stdout)
 ok=p.returncode==expected if expected is not None else p.returncode==1
 RESULT['testes'].append({'nome':name,'passou':ok,'codigo':p.returncode,'segundos':round(time.monotonic()-t,3)});save();print(('PASSOU ' if ok else 'FALHOU ')+name,flush=True)
 if not ok: print(p.stdout[-16000:].decode('utf-8',errors='replace'),flush=True);raise AssertionError(name)
 return p.stdout
EXE=ROOT/'src/santafe.exe'
def sf(name,text,cwd=ROOT,expected=0,env=None):return run(name,[EXE,'-E','-P','-'],cwd,expected,text.encode('utf-8'),env=env)
def lit(p):return json.dumps(str(p),ensure_ascii=False)
try:
 src=ROOT/'src';resources=OUT/'recursos';res=lambda n,d,lib=False:compile_resource(resources,n,d,lib);lib=src/'libsantafe-3.dll.a';dll=src/'santafe-3.dll'
 objs=[p for p in sorted(src.glob('*.o')) if p.name not in ('santafe.o','santafec.o','santafe-windows.o')]
 run('nucleo-dll',['gcc','-shared','-Wl,--export-all-symbols','-Wl,--out-implib,'+str(lib),*objs,res('santafe-3.dll','Santafé núcleo',True),'-lm','-lws2_32','-o',dll])
 run('interpretador-dll',['gcc',src/'santafe.o',src/'santafe-windows.o',res('santafe.exe','Santafé interpretador'),lib,'-lm','-lws2_32','-o',EXE])
 run('compilador-metadados',['gcc',src/'santafec.o',src/'santafe-windows.o',res('santafec.exe','Santafé compilador'),src/'libsantafe.a','-lm','-lws2_32','-o',src/'santafec.exe'])
 glibflags=subprocess.check_output(['pkg-config','--cflags','--libs','glib-2.0'],text=True).split()
 for tool in ['sls','pacotes']:
  run('compilar-'+tool,['gcc','-std=gnu99','-O2','-Wall','-Wextra','-shared','-I'+str(src),ROOT/f'ferramentas/{tool}/nativo-windows.c',res('nativo.dll','Santafé '+tool,True),lib,*glibflags,'-lbcrypt','-ladvapi32','-o',ROOT/f'ferramentas/{tool}/nativo.dll'])
 run('iniciador-sls',['gcc','-std=gnu99','-O2','-Wall','-I'+str(src),ROOT/'ferramentas/sls/iniciador-windows.c',src/'santafe-windows.o',res('santafe-sls.exe','Santafé SLS'),lib,'-o',src/'santafe-sls.exe'])
 # Copy runtime DLLs from the trusted UCRT64 toolchain, never from the workspace.
 compiler=Path(shutil.which('gcc')).resolve();trusted=compiler.parent;todo=[EXE,ROOT/'ferramentas/pacotes/nativo.dll'];done=set()
 while todo:
  binary=todo.pop()
  for line in subprocess.check_output(['objdump','-p',binary],text=True).splitlines():
   if 'DLL Name:' not in line:continue
   name=line.split('DLL Name:',1)[1].strip()
   assert name.lower() not in ('msys-2.0.dll','cygwin1.dll')
   if name.lower() in done:continue
   done.add(name.lower());origin=trusted/name;target=src/name
   if origin.is_file() and not target.exists():shutil.copyfile(origin,target);todo.append(target)
 os.environ['SANTAFE_CC']=str(compiler)
 INIT='local N=garanta(módulo.carregarBib('+lit(ROOT/'ferramentas/pacotes/nativo.dll')+',"luaopen_pacotes_nativo"))(); '
 run('compilar-sonda-confinamento',['gcc','-std=gnu99','-O2','-I'+str(ROOT),'-I'+str(src),HERE/'sonda-confinamento.c',lib,'-ladvapi32','-lbcrypt','-o',src/'sonda-confinamento.exe'])
 run('sonda-confinamento-isolada',[src/'sonda-confinamento.exe',OUT/'fixture-confinamento'])
 sf('api-basica',INIT+'garanta(N.sha256("abc")=="ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");garanta(N.decodBase64(N.base64("ação"))=="ação");garanta(#N.nonce()==32)')
 work=OUT/'projeto-ação-漢字';work.mkdir()
 sf('arquivos-atomicos',INIT+'local r=garanta(N.raiz('+lit(work)+'));garanta(r:diretorio("sub/pasta"));garanta(r:grave("sub/pasta/a.fé","José",falso));garanta(r:leia("sub/pasta/a.fé")=="José");garanta(não r:grave("sub/pasta/a.fé","erro",falso));garanta(r:grave("sub/pasta/a.fé","novo",verdadeiro));garanta(r:leia("sub/pasta/a.fé")=="novo");garanta(r:trave());r:feche()')
 run('ajuda-cli',[EXE,'instale','--ajuda'],work)
 run('sls-contrato',[sys.executable,ROOT/'testes/integracao/testar_sls_aceitacao.py','--perfil','1.0','--prazo','15','--relatorio',OUT/'sls-contrato.json','--comando',src/'santafe-sls.exe'],timeout=240)
 from casos import test
 test(ROOT,OUT,run,sf,EXE,INIT,lit)
 from portatil import prepare
 prepare(ROOT,OUT,run)
 RESULT['resultado']='passou_integracao_adversarial'
except Exception as e:
 RESULT['resultado']='falhou';RESULT['falha']=str(e);RESULT['rastro']=traceback.format_exc();traceback.print_exc()
finally:save()
sys.exit(0 if RESULT['resultado'].startswith('passou') else 1)
