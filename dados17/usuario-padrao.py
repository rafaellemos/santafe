from pathlib import Path
import ctypes,json,hashlib,os,subprocess,sys,traceback,uuid,winreg
out=Path(sys.argv[1]);package=out/'santafe.msi';meta=json.loads((out/'manifesto.json').read_text(encoding='utf-8'))
result={'resultado':'em_execucao','administrador':bool(ctypes.windll.shell32.IsUserAnAdmin()),'testes':[]}
def known(s):
 b=(ctypes.c_byte*16).from_buffer_copy(uuid.UUID(s).bytes_le);p=ctypes.c_wchar_p()
 assert ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(b),0,None,ctypes.byref(p))==0
 v=p.value;ctypes.windll.ole32.CoTaskMemFree(p);return v
def call(name,args):
 p=subprocess.run([str(Path(os.environ['SystemRoot'])/'System32/msiexec.exe'),*args,'/qn','/norestart','/l*v',str(out/(name+'.log'))],timeout=180)
 assert p.returncode==0,(name,p.returncode);result['testes'].append(name)
try:
 assert not result['administrador'],'The account must not be an administrator'
 local=known('F1B32785-6FBA-4FCF-9D55-7B8E7F157091');target=Path(local)/'Programs/Santafe-Dados-Candidato'
 result['perfil_local']=str(target)
 call('instalar-sem-administrador',['/i',str(package)])
 for n,d in meta['arquivos'].items():assert hashlib.sha256((target/n).read_bytes()).hexdigest()==d,n
 result['testes'].append('integridade-payload-completo')
 env={k:v for k,v in os.environ.items() if k.upper() in ('SYSTEMROOT','WINDIR','TEMP','TMP')};env['PATH']=str(Path(os.environ['SystemRoot'])/'System32');env['USERPROFILE']=known('5E6C858F-0E22-4760-9AFE-EA3317B67173')
 p=subprocess.run([str(target/'bin/santafe.exe'),'-e','garanta(tipo([1,nulo])=="lista"); mostre("SEM_ADMIN_OK")'],capture_output=True,env=env,timeout=30)
 assert p.returncode==0 and b'SEM_ADMIN_OK' in p.stdout,(p.returncode,p.stderr);result['testes'].append('executar-nucleo-sem-toolchain')
 p=subprocess.run([str(target/'bin/santafe.exe'),'instale','--ajuda'],capture_output=True,env=env,timeout=30);assert p.returncode==0,p.stderr;result['testes'].append('gerenciador-sem-administrador')
 call('desinstalar-sem-administrador',['/x',meta['product_code']]);assert not (target/'bin/santafe.exe').exists()
 result['resultado']='passou_usuario_padrao'
except BaseException as e:result['resultado']='falhou';result['falha']=str(e);result['rastro']=traceback.format_exc()
finally:
 (out/'usuario-padrao.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
sys.exit(0 if result['resultado'].startswith('passou') else 1)
