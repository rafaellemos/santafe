"""Build a native per-user MSI using Windows Installer APIs (build Python 3.12 only)."""
from pathlib import Path
import ctypes,hashlib,json,os,tempfile,uuid,zipfile
import msilib as m
from msilib import schema
NS=uuid.UUID('9186e94f-11da-431e-b460-61d009405012')
def guid(s):return '{'+str(uuid.uuid5(NS,s)).upper()+'}'
UPGRADE=guid('candidate-windows-x64-channel')
REG=r'Software\Santafe\CandidatoDados'
def ident(s):return 'I'+hashlib.sha256(s.encode()).hexdigest()[:30]
def build(archive,version,out,guard,fault=False):
 archive,out,guard=map(Path,(archive,out,guard));out.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(prefix='santafe-msi-') as tmp:
  tmp=Path(tmp);root=tmp/'payload';root.mkdir()
  with zipfile.ZipFile(archive) as z:
   for n in z.namelist():
    assert not n.startswith('/') and '..' not in n.split('/') and '\\' not in n and ':' not in n,n
   z.extractall(root)
  old=json.loads((root/'SHA256.json').read_text(encoding='utf-8'))
  assert {p.as_posix():d for p,d in [(Path(n),hashlib.sha256((root/n).read_bytes()).hexdigest()) for n in old]}==old
  assert len(list(p for p in root.rglob('*') if p.is_file()))==len(old)+1
  (root/'VERSAO-INSTALADOR.txt').write_text(version,encoding='utf-8')
  files=sorted(p for p in root.rglob('*') if p.is_file() and p.name!='SHA256.json')
  manifest={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
  (root/'SHA256.json').write_text(json.dumps(manifest,ensure_ascii=True,indent=2)+'\n',encoding='utf-8')
  files=sorted(p for p in root.rglob('*') if p.is_file())
  hashes={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
  product=guid('product-'+version+('-fault' if fault else ''))
  db=m.init_database(str(out),schema,'Santafe dados - candidato Windows',product,version,'Projeto Santafe')
  # Windows Installer database strings are Windows-1252; payload remains UTF-8.
  cp=tmp/'codepage.idt';cp.write_bytes(b'\r\n\r\n1252\t_ForceCodepage\r\n')
  db.Commit();db=None
  api=ctypes.WinDLL('msi');handle=ctypes.c_uint()
  api.MsiOpenDatabaseW.argtypes=[ctypes.c_wchar_p,ctypes.c_void_p,ctypes.POINTER(ctypes.c_uint)]
  api.MsiDatabaseImportW.argtypes=[ctypes.c_uint,ctypes.c_wchar_p,ctypes.c_wchar_p]
  assert api.MsiOpenDatabaseW(str(out),ctypes.c_void_p(1),ctypes.byref(handle))==0
  try:
   assert api.MsiDatabaseImportW(handle,str(tmp),cp.name)==0
   assert api.MsiDatabaseCommit(handle)==0
  finally:api.MsiCloseHandle(handle)
  db=m.OpenDatabase(str(out),m.MSIDBOPEN_TRANSACT)
  si=db.GetSummaryInformation(20);si.SetProperty(m.PID_CODEPAGE,1252);si.SetProperty(m.PID_WORDCOUNT,10);si.SetProperty(m.PID_PAGECOUNT,500);si.SetProperty(m.PID_TEMPLATE,'x64;1033');si.Persist()
  add=lambda table,rows:m.add_data(db,table,rows)
  add('Property',[(k,v) for k,v in {
   'UpgradeCode':UPGRADE,'INSTALLLEVEL':'1','ARPCOMMENTS':'Candidato isolado; nao instala servicos.','ARPHELPLINK':'https://santafé.dev.br/',
   'SecureCustomProperties':'OLDERPRODUCTS;NEWERPRODUCTS;INSTALLDIR;OLDINSTALLDIR','MSIFASTINSTALL':'0','REBOOT':'ReallySuppress','DefaultUIFont':'Normal','ARPINSTALLLOCATION':'[INSTALLDIR]'
  }.items()])
  add('Directory',[('TARGETDIR',None,'SourceDir'),('LocalAppDataFolder','TARGETDIR','.'),('ProgramsDir','LocalAppDataFolder','Programs'),('INSTALLDIR','ProgramsDir','SANTAF~1|Santafe-Dados-Candidato'),('ProgramMenuFolder','TARGETDIR','.'),('MenuDir','ProgramMenuFolder','SANTAF~1|Santafe Candidato')])
  dirs={Path('.'): 'INSTALLDIR'}
  for p in sorted({p.parent for p in files}|{a for p in files for a in p.parents if a!=root and root in a.parents},key=lambda p:len(p.parts)):
   rel=p.relative_to(root)
   if rel==Path('.'):continue
   did=ident('dir/'+rel.as_posix());dirs[rel]=did
   add('Directory',[(did,dirs[rel.parent],p.name)])
  add('Feature',[('Runtime',None,'Santafe','Nucleo, SLS e gerenciador de bibliotecas',1,1,'INSTALLDIR',0)])
  cabinet=[]
  for seq,p in enumerate(files,1):
   rel=p.relative_to(root);name=rel.as_posix();fid=ident('file/'+name);cid=ident('component/'+name);rid=ident('registry/'+name)
   add('Component',[(cid,guid('component/'+name),dirs[rel.parent],260,None,rid)])
   add('FeatureComponents',[('Runtime',cid)])
   add('Registry',[(rid,1,REG+r'\Arquivos',fid,version,cid)])
   short=f'F{seq:07d}';long=p.name
   add('File',[(fid,cid,short+'|'+long,p.stat().st_size,None,None,512,seq)])
   info=m.GetFileHash(str(p),0)
   add('MsiFileHash',[(fid,0,*[ctypes.c_int32(n).value for n in info[1:]])])
   cabinet.append((str(p),fid))
  # Dedicated registration component, no wildcard removals or machine-wide PATH.
  cid='Registration';add('Component',[(cid,guid('registration'),'INSTALLDIR',260,None,'InstallDirKey')]);add('FeatureComponents',[('Runtime',cid)])
  add('Registry',[('InstallDirKey',1,REG,'InstallDir','[INSTALLDIR]',cid)])
  add('Environment',[('UserPath','=-Path','[~];[INSTALLDIR]bin',cid)])
  add('Shortcut',[('Console','MenuDir','SANTAF~1|Santafe candidato',cid,'[INSTALLDIR]bin\\santafe.exe',None,'Santafe candidato - console',None,None,None,1,'INSTALLDIR')])
  add('RemoveFile',[('RemoveEmptyMenu',cid,None,'MenuDir',2)])
  cab=tmp/'payload.cab';m.FCICreate(str(cab),cabinet);m.add_stream(db,'payload.cab',str(cab));add('Media',[(1,len(files),None,'#payload.cab',None,None)])
  add('Upgrade',[(UPGRADE,None,version,None,0,None,'OLDERPRODUCTS'),(UPGRADE,version,None,None,2,None,'NEWERPRODUCTS')])
  add('AppSearch',[('OLDINSTALLDIR','PreviousDir')]);add('RegLocator',[('PreviousDir',1,REG,'InstallDir',2|16)])
  add('LaunchCondition',[('VersionNT64 >= 603','Requer Windows x64 10 ou posterior (homologado em Server 2022).'),('NOT ALLUSERS','Instale apenas para o usuario atual.'),('NOT NEWERPRODUCTS','Uma versao mais recente ja esta instalada. A reversao deliberada exige desinstalacao primeiro.'),('NOT DISABLEROLLBACK','A reversao transacional do Windows Installer deve estar habilitada.')])
  add('Binary',[('Guard',m.Binary(str(guard)))])
  ca=[('RestoreDir',51,'INSTALLDIR','[OLDINSTALLDIR]'),('ValidateTarget',1,'Guard','ValidateTarget')]
  if fault:ca += [('SetFaultData',51,'AbortAfterFiles','[INSTALLDIR]|'+version),('AbortAfterFiles',1025,'Guard','AbortAfterFiles')]
  add('CustomAction',ca)
  prefix=[('FindRelatedProducts',None,200),('AppSearch',None,400),('LaunchConditions',None,500),('RestoreDir','OLDINSTALLDIR AND NOT INSTALLDIR',600),('CostInitialize',None,800),('FileCost',None,900),('CostFinalize',None,1000),('ValidateTarget','NOT REMOVE',1100)]
  execute=prefix+[('InstallValidate',None,1400),('InstallInitialize',None,1500),('RemoveExistingProducts','OLDERPRODUCTS',1510),('ProcessComponents',None,1600),('UnpublishFeatures',None,1800),('RemoveRegistryValues',None,2600),('RemoveShortcuts',None,3200),('RemoveEnvironmentStrings',None,3300),('RemoveFiles',None,3500),('RemoveFolders',None,3600),('CreateFolders',None,3700),('InstallFiles',None,4000),('CreateShortcuts',None,4500),('WriteRegistryValues',None,5000),('WriteEnvironmentStrings',None,5200),('RegisterUser',None,6000),('RegisterProduct',None,6100),('PublishFeatures',None,6300),('PublishProduct',None,6400),('InstallFinalize',None,6600)]
  if fault:execute += [('SetFaultData','NOT REMOVE',4010),('AbortAfterFiles','NOT REMOVE',4020)]
  add('InstallExecuteSequence',execute)
  add('TextStyle',[('Normal','Segoe UI',9,0,0),('Title','Segoe UI',13,0,1)])
  dialogs=[];controls=[];events=[]
  def dialog(name,title,text,buttons):
   dialogs.append((name,50,50,380,190,3,title,buttons[0][0],buttons[0][0],buttons[-1][0]))
   controls.append((name,'Text','Text',20,20,340,110,3,None,text,None,None))
   for i,(bid,label,evs) in enumerate(buttons):
    controls.append((name,bid,'PushButton',20+i*115,150,105,22,3,None,label,buttons[(i+1)%len(buttons)][0],None))
    for order,(event,arg) in enumerate(evs,1):events.append((name,bid,event,arg,'1',order))
  dialog('Welcome','Santafe - candidato','Instala nucleo, SLS e gerenciador para este usuario. Adiciona o diretorio bin ao PATH do usuario. Abra um terminal novo apos instalar.\n\nCandidato de homologacao, sem assinatura Authenticode; nao instala servicos.', [('Install','Instalar',[('EndDialog','Return')]),('Cancel','Cancelar',[('EndDialog','Exit')])])
  dialog('Maintenance','Santafe - manutencao','Reparar restaura os arquivos do pacote. Remover preserva arquivos extras e projetos do usuario.', [('Repair','Reparar',[('[REINSTALL]','ALL'),('[REINSTALLMODE]','amus'),('EndDialog','Return')]),('Remove','Remover',[('[REMOVE]','ALL'),('EndDialog','Return')]),('Cancel','Cancelar',[('EndDialog','Exit')])])
  for name,text,result in [('Finished','Operacao concluida. Abra um terminal novo para usar santafe e santafe-sls.','Return'),('FatalError','A operacao falhou. Consulte o log do Windows Installer.','Exit'),('Cancelled','Operacao cancelada.','Exit')]:dialog(name,'Santafe',text,[('Close','Fechar',[('EndDialog',result)])])
  add('Dialog',dialogs);add('Control',controls);add('ControlEvent',events)
  add('InstallUISequence',prefix+[('Welcome','NOT Installed',1200),('Maintenance','Installed',1201),('ExecuteAction',None,1300),('Finished',None,-1),('Cancelled',None,-2),('FatalError',None,-3)])
  db.Commit();db=None
 meta={'versao_msi':version,'candidato':'dados.17' if version=='3.0.17' else 'fixture','product_code':product,'upgrade_code':UPGRADE,'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'arquivos':hashes,'falha_injetada':fault,'assinatura_authenticode':False,'per_usuario':True,'bytes':out.stat().st_size}
 out.with_suffix('.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 return meta
if __name__=='__main__':
 import sys
 build(sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4],len(sys.argv)>5 and sys.argv[5]=='--falha-teste')
