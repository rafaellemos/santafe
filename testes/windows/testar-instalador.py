"""Native MSI lifecycle on an ephemeral Windows runner; never deploy services."""
from pathlib import Path
import ctypes,hashlib,json,os,shutil,subprocess,sys,time,traceback,uuid,winreg
import msi
import proprietario
import zipfile
HERE=Path(__file__).resolve().parent
OUT=Path(sys.argv[1]).resolve();OUT.mkdir(parents=True,exist_ok=True)
TOOLS=Path(sys.argv[2]).resolve();SOURCE=Path(sys.argv[3]).resolve();GUARD=Path(sys.argv[4]).resolve();BASE=Path(sys.argv[5]).resolve()
RESULT={'distribuicao':'3.0.0', 'baseline':'fixture dados16 reempacotada como2.9.0; não é versão pública','resultado':'em_execucao','sistema':'Windows Server 2022 x64','testes':[],'producao_alterada':False,'gui_inspecionada':False,'assinatura_authenticode':False}
def save(): (OUT/'resultado.json').write_text(json.dumps(RESULT,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def ok(name,**more):RESULT['testes'].append({'nome':name,'resultado':'passou',**more});save();print('OK',name,flush=True)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def machinepath():
 with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment') as k:return winreg.QueryValueEx(k,'Path')
def regpath():
 with winreg.OpenKey(winreg.HKEY_CURRENT_USER,'Environment') as k:
  try:return winreg.QueryValueEx(k,'Path')
  except FileNotFoundError:return None
def setpath(v):
 with winreg.OpenKey(winreg.HKEY_CURRENT_USER,'Environment',0,winreg.KEY_SET_VALUE) as k:
  if v is None:
   try:winreg.DeleteValue(k,'Path')
   except FileNotFoundError:pass
  else:winreg.SetValueEx(k,'Path',0,v[1],v[0])
def state(code):
 api=ctypes.WinDLL('msi');api.MsiQueryProductStateW.argtypes=[ctypes.c_wchar_p];api.MsiQueryProductStateW.restype=ctypes.c_int
 return api.MsiQueryProductStateW(code)
def install(name,args,expected=0,tag=None):
 log=OUT/(name+'.log');cmd=[str(Path(os.environ['SystemRoot'])/'System32/msiexec.exe'),*map(str,args),'/qn','/norestart','/l*v',str(log)]
 p=subprocess.run(cmd,timeout=180)
 text=log.read_text(encoding='utf-16',errors='replace') if log.exists() else ''
 assert p.returncode==expected,(name,p.returncode,expected,text[-4000:])
 if tag:assert tag in text,(name,'tag not present',tag)
 ok(name,codigo=p.returncode,marcador=tag)
def checkfiles(meta,target,label):
 for n,h in meta['arquivos'].items():assert (target/n).is_file() and digest(target/n)==h,(label,n)
 ok(label,arquivos=len(meta['arquivos']))
def run(name,args,env=None,timeout=240):
 p=subprocess.run(list(map(str,args)),capture_output=True,timeout=timeout,env=env)
 (OUT/(name+'.log')).write_bytes(p.stdout+b'\nSTDERR\n'+p.stderr)
 assert p.returncode==0,(name,p.returncode,p.stderr[-1500:]);ok(name)
uid=uuid.uuid4().hex[:10]; programs=Path(os.environ['LOCALAPPDATA'])/'Programs';programs.mkdir(exist_ok=True)
target=programs/('Santafe-Homologação-'+uid);foreign=programs/('Santafe-Externa-'+uid);junction=programs/('Santafe-Junção-'+uid)
workspace=OUT/'projeto-ação';workspace.mkdir();(workspace/'meu-arquivo.fé').write_text('mostre("preservar")',encoding='utf-8')
userbytes=(workspace/'meu-arquivo.fé').read_bytes();machine_before=machinepath();original=regpath();prefix=str(programs/('OutroPrograma-'+uid));suffix=str(programs/('ProgramaPosterior-'+uid))
seed=(original[0]+';' if original else '')+prefix;setpath((seed,winreg.REG_EXPAND_SZ))
oldmsi=OUT/'fixture-dados16.msi';newmsi=OUT/'santafe-3.0.0-windows-x64.msi';badmsi=OUT/'fixture-falha21.msi'
metas=[]
try:
 assert digest(BASE)=='84be8651b8e41787524f4be13ce27a6d3a9be185a3f12537891e2108773a26a4'
 portable=TOOLS/'santafe-3.0.0-windows-x64-portatil.zip'
 old=msi.build(BASE,'2.9.0',oldmsi,GUARD);new=msi.build(portable,'3.0.0',newmsi,GUARD);bad=msi.build(portable,'3.0.1',badmsi,GUARD,True);metas=[old,new,bad]
 for meta,path in zip(metas,(oldmsi,newmsi,badmsi)):assert digest(path)==meta['sha256'],('hash-apos-fechar-msi',path.name)
 run('validacao-estrutural-ice',[sys.executable,HERE/'validar-msi.py',newmsi,OUT])
 ok('msi-construido-api-nativa',baseline_sha256=digest(BASE),msi_sha256=new['sha256'])
 # Validate real database, not only generator metadata.
 db=msi.m.OpenDatabase(str(newmsi),msi.m.MSIDBOPEN_READONLY)
 view=db.OpenView('SELECT `Action`, `Type` FROM `CustomAction`');view.Execute(None);actions=[]
 while (row:=view.Fetch()):actions.append((row.GetString(1),row.GetInteger(2)))
 assert set(actions)=={('RestoreDir',51),('ValidateTarget',1),('RejectUnsupportedMode',19)}
 db=None;ok('msi-publicavel-sem-injecao-de-falha')
 adminimage=OUT/'imagem-administrativa-recusada'
 install('recusa-imagem-administrativa',['/a',newmsi,'TARGETDIR='+str(adminimage)],1603)
 assert not adminimage.exists() and state(new['product_code'])==-1
 ok('imagem-administrativa-nao-gravou-produto')
 # Windows Installer advertisement only registers availability, not installation.
 # Custom actions are forbidden in AdvtExecuteSequence; preserve standard behavior.
 default_target=programs/'Santafe'
 assert not default_target.exists()
 before_advertise=regpath()
 install('anunciar-sem-instalar',['/ju',newmsi])
 assert state(new['product_code'])==1 and not default_target.exists() and regpath()==before_advertise
 ok('anuncio-sem-payload-sem-path')
 install('remover-anuncio',['/x',newmsi])
 assert state(new['product_code'])==-1 and not default_target.exists() and regpath()==before_advertise
 ok('anuncio-removido-sem-residuos')
 foreign.mkdir();(foreign/'documento.txt').write_text('arquivo do usuario',encoding='utf-8')
 install('recusa-diretorio-nao-pertencente',['/i',newmsi,'INSTALLDIR='+str(foreign)],1603,'DADOS20_TARGET_NOT_EMPTY')
 assert (foreign/'documento.txt').read_text()=='arquivo do usuario'
 install('recusa-instalacao-por-maquina',['/i',newmsi,'ALLUSERS=1','INSTALLDIR='+str(target)],1603)
 install('recusa-sem-reversao',['/i',newmsi,'DISABLEROLLBACK=1','INSTALLDIR='+str(target)],1603)
 assert not target.exists()
 # Positive control: junction really resolves before preflight refuses it.
 subprocess.run([os.environ['COMSPEC'],'/d','/c','mklink','/J',str(junction),str(foreign)],check=True,capture_output=True)
 assert (junction/'documento.txt').read_text()=='arquivo do usuario'
 install('recusa-juncao',['/i',newmsi,'INSTALLDIR='+str(junction)],1603,'DADOS20_TARGET_REPARSE_OR_FILE')
 os.rmdir(junction);ok('controle-positivo-juncao')
 install('falha-primeira-instalacao',['/i',badmsi,'INSTALLDIR='+str(target)],1603,'DADOS20_FALHA_APOS_COPIA_CONFIRMADA')
 assert state(bad['product_code'])==-1 and not (target/'bin/santafe.exe').exists();ok('reversao-primeira-instalacao-sem-registro')
 install('instalar-baseline16',['/i',oldmsi,'INSTALLDIR='+str(target)])
 assert state(old['product_code'])==5;checkfiles(old,target,'baseline16-integridade')
 entry=str(target/'bin');assert entry.lower() in regpath()[0].lower() and prefix in regpath()[0];ok('path-do-usuario-preservado')
 extra=target/'documento-pessoal.txt';extra.write_text('nao excluir',encoding='utf-8')
 hard=foreign/'hardlink.txt';os.link(target/'LEIA-ME.txt',hard)
 install('recusa-hardlink-em-atualizacao',['/i',newmsi],1603,'DADOS20_TARGET_UNSAFE_ENTRY');hard.unlink()
 binpath=target/'bin';savedbin=target/'bin-original';binpath.rename(savedbin)
 subprocess.run([os.environ['COMSPEC'],'/d','/c','mklink','/J',str(binpath),str(foreign)],check=True,capture_output=True)
 install('recusa-juncao-interna-em-atualizacao',['/i',newmsi],1603,'DADOS20_TARGET_UNSAFE_ENTRY');os.rmdir(binpath);savedbin.rename(binpath)
 checkfiles(old,target,'recusas-preservaram-baseline16')
 install('falha-real-depois-da-copia',['/i',badmsi],1603,'DADOS20_FALHA_APOS_COPIA_CONFIRMADA')
 assert state(old['product_code'])==5 and state(bad['product_code'])==-1
 checkfiles(old,target,'reversao-restaurou-baseline16');assert extra.read_text()=='nao excluir';ok('reversao-preservou-extras')
 install('atualizar-16-para-20',['/i',newmsi])
 assert state(new['product_code'])==5 and state(old['product_code'])==-1;checkfiles(new,target,'instalacao20-integridade')
 assert regpath()[0].lower().count(entry.lower())==1;ok('atualizacao-sem-duplicar-path')
 install('recusar-retrocesso-acidental',['/i',oldmsi],1603);checkfiles(new,target,'recusa-preservou20')
 env={k:v for k,v in os.environ.items() if k.upper() in ('SYSTEMROOT','WINDIR','TEMP','TMP','USERPROFILE')};env['PATH']=str(Path(os.environ['SystemRoot'])/'System32')
 run('instalado-versao',[target/'bin/santafe.exe','-v'],env)
 run('instalado-sls39',[sys.executable,HERE/'portatil_sls.py',SOURCE,target/'bin/santafe-sls.exe',OUT/'sls-instalado.json'],env)
 # Installation is not the project: project state remains outside the installation.
 # Reproduce data16's owner bug under the same native elevated token.
 token_user=proprietario.token_sid(1);token_default=proprietario.token_sid(4)
 assert token_user!=token_default,'This regression requires an administrative token with a group default owner'
 oldruntime=OUT/'runtime16';oldwork=OUT/'projeto-proprietario16';oldwork.mkdir()
 with zipfile.ZipFile(BASE) as z:z.extractall(oldruntime)
 oldtest=subprocess.run([str(oldruntime/'bin/santafe.exe'),'instale','exemplo','1.0.0','--repositorio-local',str(TOOLS/'casos/repo')],cwd=oldwork,capture_output=True,env=env,timeout=60)
 assert oldtest.returncode==1 and b'Win32 5' in oldtest.stderr
 assert proprietario.file_owner(oldwork/'.santafe/trava')==token_default
 ok('controle-positivo-defeito-proprietario16')
 p=subprocess.run([str(target/'bin/santafe.exe'),'instale','exemplo','1.0.0','--repositorio-local',str(TOOLS/'casos/repo')],cwd=workspace,capture_output=True,env=env,timeout=60)
 assert p.returncode==0,p.stderr;ok('gerenciador-instalado-projeto-separado')
 assert proprietario.file_owner(workspace/'.santafe/trava')==token_user;ok('trava-criada-com-proprietario-usuario')
 foreignlock=OUT/'projeto-trava-alheia';(foreignlock/'.santafe').mkdir(parents=True);lock=foreignlock/'.santafe/trava';lock.write_bytes(b'')
 proprietario.set_owner(lock,token_default);assert proprietario.file_owner(lock)!=token_user
 refused=subprocess.run([str(target/'bin/santafe.exe'),'instale','exemplo','1.0.0','--repositorio-local',str(TOOLS/'casos/repo')],cwd=foreignlock,capture_output=True,env=env,timeout=60)
 assert refused.returncode==1 and b'Win32 5' in refused.stderr;assert not (foreignlock/'santafe.json').exists();ok('trava-alheia-continua-recusada')
 p=subprocess.run([str(target/'bin/santafe.exe'),'-e','garanta((importe "exemplo").valor==42)'],cwd=workspace,capture_output=True,env=env,timeout=60);assert p.returncode==0,p.stderr;ok('biblioteca-importada-apos-instalar')
 project_hashes={p.relative_to(workspace).as_posix():digest(p) for p in workspace.rglob('*') if p.is_file()}
 (target/'share/santafé/3.0/ferramentas/sls/nativo.dll').unlink();(target/'LEIA-ME.txt').write_text('dano sintetico',encoding='utf-8')
 install('reparar-arquivos-ausentes-e-corrompidos',['/fa',newmsi]);checkfiles(new,target,'reparacao-integridade')
 # Uninstall cannot follow a replaced managed directory into unrelated files.
 (foreign/'santafe.exe').write_bytes(b'arquivo alheio nao remover')
 binpath.rename(savedbin)
 subprocess.run([os.environ['COMSPEC'],'/d','/c','mklink','/J',str(binpath),str(foreign)],check=True,capture_output=True)
 try:
  install('recusa-juncao-na-desinstalacao',['/x',new['product_code']],1603,'DADOS20_TARGET_UNSAFE_ENTRY')
  assert (foreign/'santafe.exe').read_bytes()==b'arquivo alheio nao remover' and state(new['product_code'])==5
 finally:
  os.rmdir(binpath);savedbin.rename(binpath)
 checkfiles(new,target,'remocao-recusada-preservou-instalacao')
 setpath((regpath()[0]+';'+suffix,winreg.REG_EXPAND_SZ))
 install('desinstalar20',['/x',new['product_code']])
 assert state(new['product_code'])==-1 and not (target/'bin/santafe.exe').exists()
 assert extra.read_text()=='nao excluir' and (workspace/'meu-arquivo.fé').read_bytes()==userbytes
 assert {p.relative_to(workspace).as_posix():digest(p) for p in workspace.rglob('*') if p.is_file()}==project_hashes
 current=regpath()[0];assert entry.lower() not in current.lower() and prefix in current and suffix in current;ok('desinstalacao-preservou-projetos-extras-e-path')
 # Deliberate rollback after successful update: explicit uninstall then baseline reinstall.
 extra.unlink();shutil.rmtree(target) # Only this harness-owned empty residual tree.
 install('reversao-deliberada-reinstalar16',['/i',oldmsi,'INSTALLDIR='+str(target)]);checkfiles(old,target,'reversao-deliberada-integridade16')
 install('remover-baseline16',['/x',old['product_code']])
 assert state(old['product_code'])==-1;ok('ciclo-encerrado-sem-produto-registrado')
 assert machinepath()==machine_before;ok('path-da-maquina-inalterado')
 assert digest(newmsi)==new['sha256'];ok('msi-entregue-inalterado-apos-todos-ensaios')
 RESULT['resultado']='passou_instalacao_atualizacao_reversao';RESULT['msi']=new
except BaseException as e:
 RESULT['resultado']='falhou';RESULT['falha']=str(e);RESULT['rastro']=traceback.format_exc();traceback.print_exc()
finally:
 for meta in reversed(metas):
  if state(meta['product_code'])==5:
   try:install('limpeza-'+meta['versao_msi'],['/x',meta['product_code']])
   except Exception:RESULT['limpeza_pendente']=True
 setpath(original);save()
 print('RESULTADO_INSTALADOR',RESULT['resultado'],flush=True)
sys.exit(0 if RESULT['resultado'].startswith('passou') else 1)
