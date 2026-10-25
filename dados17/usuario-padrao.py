from pathlib import Path
import ctypes,json,hashlib,os,subprocess,sys,traceback,uuid,winreg
out=Path(sys.argv[1]);package=out/'santafe.msi';meta=json.loads((out/'manifesto.json').read_text(encoding='utf-8'))
policy_test=len(sys.argv)>2 and sys.argv[2]=='politica-bloqueia'
result={'resultado':'em_execucao','administrador':bool(ctypes.windll.shell32.IsUserAnAdmin()),'testes':[]}
def known(s):
 b=(ctypes.c_byte*16).from_buffer_copy(uuid.UUID(s).bytes_le);p=ctypes.c_wchar_p()
 rc=ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(b),0x8000,None,ctypes.byref(p));assert rc==0,('SHGetKnownFolderPath',s,hex(rc & 0xffffffff))
 v=p.value;ctypes.windll.ole32.CoTaskMemFree(p);return v
def call(name,args,expected=0):
 p=subprocess.run([str(Path(os.environ['SystemRoot'])/'System32/msiexec.exe'),*args,'/qn','/norestart','/l*v',str(out/(name+'.log'))],timeout=180)
 assert p.returncode==expected,(name,p.returncode,expected);result['testes'].append(name)
try:
 assert not result['administrador'],'The account must not be an administrator'
 assert hashlib.sha256(package.read_bytes()).hexdigest()==meta['sha256'],'Hash of the MSI differs from the tested package'
 # Start-Process -Credential does not supply a fresh per-user environment.
 # Obtain it from Windows for this token, instead of inheriting runneradmin's.
 from ctypes import wintypes as w
 kernel=ctypes.WinDLL('kernel32');adv=ctypes.WinDLL('advapi32');userenv=ctypes.WinDLL('userenv')
 kernel.GetCurrentProcess.restype=w.HANDLE;kernel.CloseHandle.argtypes=[w.HANDLE]
 adv.OpenProcessToken.argtypes=[w.HANDLE,w.DWORD,ctypes.POINTER(w.HANDLE)]
 userenv.CreateEnvironmentBlock.argtypes=[ctypes.POINTER(ctypes.c_void_p),w.HANDLE,w.BOOL];userenv.DestroyEnvironmentBlock.argtypes=[ctypes.c_void_p]
 token=w.HANDLE();block=ctypes.c_void_p();assert adv.OpenProcessToken(kernel.GetCurrentProcess(),10,ctypes.byref(token))
 try:
  assert userenv.CreateEnvironmentBlock(ctypes.byref(block),token,False)
  try:
   clean={};cursor=block.value
   while True:
    line=ctypes.wstring_at(cursor)
    if not line:break
    cursor+=(len(line)+1)*ctypes.sizeof(ctypes.c_wchar)
    if not line.startswith('='):
     key,value=line.split('=',1);clean[key]=value
   os.environ.clear();os.environ.update(clean)
  finally:userenv.DestroyEnvironmentBlock(block)
 finally:kernel.CloseHandle(token)
 local=known('F1B32785-6FBA-4FCF-9D55-7B8E7F157091');target=Path(local)/'Programs/Santafe-Dados-Candidato'
 result['perfil_local']=str(target)
 if policy_test:
  call('recusar-por-politica',['/i',str(package)],1625)
  assert not (target/'bin/santafe.exe').exists()
  result['resultado']='passou_recusa_por_politica'
  raise SystemExit(0)
 call('instalar-sem-administrador',['/i',str(package)])
 for n,d in meta['arquivos'].items():assert hashlib.sha256((target/n).read_bytes()).hexdigest()==d,n
 result['testes'].append('integridade-payload-completo')
 env={k:v for k,v in os.environ.items() if k.upper() in ('SYSTEMROOT','WINDIR','TEMP','TMP')};env['PATH']=str(Path(os.environ['SystemRoot'])/'System32');env['USERPROFILE']=known('5E6C858F-0E22-4760-9AFE-EA3317B67173')
 p=subprocess.run([str(target/'bin/santafe.exe'),'-e','garanta(tipo([1,nulo])=="lista"); mostre("SEM_ADMIN_OK")'],capture_output=True,env=env,timeout=30)
 assert p.returncode==0 and b'SEM_ADMIN_OK' in p.stdout,(p.returncode,p.stderr);result['testes'].append('executar-nucleo-sem-toolchain')
 p=subprocess.run([str(target/'bin/santafe.exe'),'instale','--ajuda'],capture_output=True,env=env,timeout=30);assert p.returncode==0,p.stderr;result['testes'].append('gerenciador-sem-administrador')
 call('desinstalar-sem-administrador',['/x',meta['product_code']]);assert not (target/'bin/santafe.exe').exists()
 result['resultado']='passou_usuario_padrao'
except SystemExit:
 if not result['resultado'].startswith('passou'):raise
except BaseException as e:result['resultado']='falhou';result['falha']=str(e);result['rastro']=traceback.format_exc()
finally:
 (out/('politica-usuario-padrao.json' if policy_test else 'usuario-padrao.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
sys.exit(0 if result['resultado'].startswith('passou') else 1)
