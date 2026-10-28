"""Build a native per-user MSI using Windows Installer APIs (build Python 3.12 only)."""
from pathlib import Path
import ctypes,hashlib,json,os,tempfile,uuid,zipfile
import msilib as m
from msilib import schema
from licencas import verify_archive
NS=uuid.UUID('9186e94f-11da-431e-b460-61d009405012')
def guid(s):return '{'+str(uuid.uuid5(NS,s)).upper()+'}'
UPGRADE=guid('stable-windows-x64-channel')
REG=r'Software\Santafe\Estavel'
def ident(s):return 'I'+hashlib.sha256(s.encode()).hexdigest()[:30]
def build(archive,version,out,guard,fault=False):
 archive,out,guard=map(Path,(archive,out,guard));out.parent.mkdir(parents=True,exist_ok=True)
 # Old baseline 3.0.16 is only a regression fixture; every new candidate must have notices.
 if tuple(map(int,version.split('.'))) >= (3,0,0):
  verify_archive(archive)
  from dependencias import verify_package
  with zipfile.ZipFile(archive) as z:verify_package(z.read)
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
  product=guid('stable-product-'+version+('-fault' if fault else ''))
  db=m.init_database(str(out),schema,'Santafé 3 — Windows',product,version,'Projeto Santafe')
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
  si=db.GetSummaryInformation(20);si.SetProperty(m.PID_CODEPAGE,1252);si.SetProperty(m.PID_WORDCOUNT,10);si.SetProperty(m.PID_PAGECOUNT,500);si.SetProperty(m.PID_TEMPLATE,'x64;1046');si.Persist();si=None
  # Release the summary handle before final database close and SHA-256.
  # Otherwise native storage may finish its write after build() returns.
  add=lambda table,rows:m.add_data(db,table,rows)
  db.OpenView("UPDATE `Property` SET `Value` = '1046' WHERE `Property` = 'ProductLanguage'").Execute(None)
  add('Property',[(k,v) for k,v in {
   'UpgradeCode':UPGRADE,'INSTALLLEVEL':'1','ARPCOMMENTS':'Núcleo, SLS e gerenciador; instalação por usuário, sem serviços.','ARPHELPLINK':'https://santafé.dev.br/',
   'SecureCustomProperties':'OLDERPRODUCTS;NEWERPRODUCTS;INSTALLDIR;OLDINSTALLDIR','MSIFASTINSTALL':'0','REBOOT':'ReallySuppress','DefaultUIFont':'Normal','ErrorDialog':'ErrorDlg','ARPINSTALLLOCATION':'[INSTALLDIR]'
  }.items()])
  add('Directory',[('TARGETDIR',None,'SourceDir'),('LocalAppDataFolder','TARGETDIR','.'),('ProgramsDir','LocalAppDataFolder','Programs'),('INSTALLDIR','ProgramsDir','SANTAF~1|Santafe'),('ProgramMenuFolder','TARGETDIR','.'),('MenuDir','ProgramMenuFolder','SANTAF~1|Santafe')])
  dirs={Path('.'): 'INSTALLDIR'}
  for number,p in enumerate(sorted({p.parent for p in files}|{a for p in files for a in p.parents if a!=root and root in a.parents},key=lambda p:(len(p.parts),p.as_posix())),1):
   rel=p.relative_to(root)
   if rel==Path('.'):continue
   did=ident('dir/'+rel.as_posix());dirs[rel]=did
   add('Directory',[(did,dirs[rel.parent],f'D{number:07d}|'+p.name)])
  add('Feature',[('Runtime',None,'Santafe','Nucleo, SLS e gerenciador de bibliotecas',1,1,'INSTALLDIR',0)])
  cabinet=[]
  for seq,p in enumerate(files,1):
   rel=p.relative_to(root);name=rel.as_posix();fid=ident('file/'+name);cid=ident('component/'+name);rid=ident('registry/'+name)
   add('Component',[(cid,guid('stable-component/'+name),dirs[rel.parent],260,None,rid)])
   add('FeatureComponents',[('Runtime',cid)])
   add('Registry',[(rid,1,REG+r'\Arquivos',fid,version,cid)])
   short=f'F{seq:07d}';long=p.name
   add('File',[(fid,cid,short+'|'+long,p.stat().st_size,None,None,512,seq)])
   class FileHash(ctypes.Structure):_fields_=[('size',ctypes.c_uint32),('parts',ctypes.c_uint32*4)]
   info=FileHash();info.size=ctypes.sizeof(info)
   api.MsiGetFileHashW.argtypes=[ctypes.c_wchar_p,ctypes.c_uint,ctypes.POINTER(FileHash)]
   assert api.MsiGetFileHashW(str(p),0,ctypes.byref(info))==0
   add('MsiFileHash',[(fid,0,*[ctypes.c_int32(n).value for n in info.parts])])
   cabinet.append((str(p),fid))
  # Dedicated registration component, no wildcard removals or machine-wide PATH.
  cid='Registration';add('Component',[(cid,guid('stable-registration'),'INSTALLDIR',260,None,'InstallDirKey')]);add('FeatureComponents',[('Runtime',cid)])
  add('Registry',[('InstallDirKey',1,REG,'InstallDir','[INSTALLDIR]',cid)])
  add('Environment',[('UserPath','=-Path','[~];[INSTALLDIR]bin',cid)])
  add('Shortcut',[('Console','MenuDir','SANTAF~1|Santafe',cid,'[INSTALLDIR]bin\\santafe.exe',None,'Santafe - console',None,None,None,1,'INSTALLDIR')])
  # Remove only empty managed directories; never wildcard/delete user files.
  add('RemoveFile',[(ident('empty/'+d),cid,None,d,2) for d in ['MenuDir','ProgramsDir',*dirs.values()]])
  cab=tmp/'payload.cab';m.FCICreate(str(cab),cabinet);m.add_stream(db,'payload.cab',str(cab));add('Media',[(1,len(files),None,'#payload.cab',None,None)])
  add('Upgrade',[(UPGRADE,None,version,None,0,None,'OLDERPRODUCTS'),(UPGRADE,version,None,None,2,None,'NEWERPRODUCTS')])
  add('AppSearch',[('OLDINSTALLDIR','PreviousDir')]);add('RegLocator',[('PreviousDir',1,REG,'InstallDir',2|16)])
  add('LaunchCondition',[('VersionNT64 >= 603','Requer Windows x64 10 ou posterior (homologado em Server 2022).'),('NOT ALLUSERS','Instale apenas para o usuario atual.'),('NOT NEWERPRODUCTS','Uma versao mais recente ja esta instalada. A reversao deliberada exige desinstalacao primeiro.'),('NOT DISABLEROLLBACK AND NOT RollbackDisabled','A reversao transacional do Windows Installer deve estar habilitada.')])
  add('Binary',[('Guard',m.Binary(str(guard)))])
  ca=[('RestoreDir',51,'INSTALLDIR','[OLDINSTALLDIR]'),('ValidateTarget',1,'Guard','ValidateTarget'),('RejectUnsupportedMode',19,None,'Esta distribuição aceita instalação por usuário. Imagem administrativa não é suportada.')]
  if fault:ca += [('SetFaultData',51,'AbortAfterFiles','[INSTALLDIR]|'+version),('AbortAfterFiles',1025,'Guard','AbortAfterFiles')]
  add('CustomAction',ca)
  prefix=[('FindRelatedProducts',None,200),('AppSearch',None,400),('LaunchConditions',None,500),('RestoreDir','OLDINSTALLDIR AND NOT INSTALLDIR',600),('CostInitialize',None,800),('FileCost',None,900),('CostFinalize',None,1000),('ValidateTarget',None,1100)]
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
  dialog('Welcome','Santafé — instalação','Instala núcleo, SLS e gerenciador para este usuário. Adiciona o diretório bin ao PATH do usuário. Abra um terminal novo após instalar.\n\nSem assinatura Authenticode; confira a origem e o SHA-256 no portal oficial. Não instala serviços.', [('Install','Instalar',[('EndDialog','Return')]),('Cancel','Cancelar',[('EndDialog','Exit')])])
  dialog('Maintenance','Santafé — manutenção','Reparar restaura os arquivos do pacote. Remover preserva arquivos extras e projetos do usuário.', [('Repair','Reparar',[('[REINSTALL]','ALL'),('[REINSTALLMODE]','amus'),('EndDialog','Return')]),('Remove','Remover',[('[REMOVE]','ALL'),('EndDialog','Return')]),('Cancel','Cancelar',[('EndDialog','Exit')])])
  for name,text,result in [('Finished','Operação concluída.','Return'),('FatalError','A operação falhou. Consulte o registro do Windows Installer.','Exit'),('Cancelled','Operação cancelada.','Exit')]:dialog(name,'Santafé',text,[('Close','Fechar',[('EndDialog',result)])])
  # Required Windows Installer dialogs: file conflicts and dynamic errors.
  dialogs.append(('FilesInUse',50,50,420,220,3,'Santafé — arquivos em uso','Retry','Retry','Cancel'))
  controls.extend([('FilesInUse','Text','Text',20,15,380,45,3,None,'Feche os aplicativos abaixo e tente novamente. Cancelar preserva a instalação anterior.',None,None),('FilesInUse','Processes','ListBox',20,65,380,95,3,'FileInUseProcess',None,None,None)])
  for i,(bid,label,arg,nextid) in enumerate([('Retry','Tentar novamente','Retry','Ignore'),('Ignore','Ignorar','Ignore','Cancel'),('Cancel','Cancelar','Exit','Retry')]):
   controls.append(('FilesInUse',bid,'PushButton',20+i*130,180,120,24,3,None,label,nextid,None))
   events.append(('FilesInUse',bid,'EndDialog',arg,'1',1))
  dialogs.append(('ErrorDlg',50,50,420,190,65539,'Santafé','ErrorText','O','C'))
  controls.append(('ErrorDlg','ErrorText','Text',20,20,380,105,3,None,'[ErrorText]','A',None))
  errorbuttons=[('A','Interromper','ErrorAbort'),('C','Cancelar','ErrorCancel'),('I','Ignorar','ErrorIgnore'),('N','Não','ErrorNo'),('O','OK','ErrorOk'),('R','Tentar novamente','ErrorRetry'),('Y','Sim','ErrorYes')]
  for i,(bid,label,arg) in enumerate(errorbuttons):
   controls.append(('ErrorDlg',bid,'PushButton',20,145,120,24,3,None,label,errorbuttons[i+1][0] if i+1<len(errorbuttons) else 'ErrorText',None))
   events.append(('ErrorDlg',bid,'EndDialog',arg,'1',1))
  add('Dialog',dialogs);add('Control',controls);add('ControlEvent',events)
  # Administrative images are refused before writes. Advertisement uses only
  # standard MSI actions (custom actions are forbidden here); no payload executes.
  cost=[('CostInitialize',None,800),('FileCost',None,900),('CostFinalize',None,1000)]
  endings=[('Finished',None,-1),('Cancelled',None,-2),('FatalError',None,-3)]
  add('AdminUISequence',[('RejectUnsupportedMode',None,100),*cost,('ExecuteAction',None,1300),*endings])
  add('AdminExecuteSequence',[('RejectUnsupportedMode',None,100),*cost,('InstallValidate',None,1400),('InstallInitialize',None,1500),('InstallAdminPackage',None,3900),('InstallFiles',None,4000),('InstallFinalize',None,6600)])
  add('AdvtExecuteSequence',[('CostInitialize',None,800),('CostFinalize',None,1000),('InstallValidate',None,1400),('InstallInitialize',None,1500),('PublishFeatures',None,6300),('PublishProduct',None,6400),('InstallFinalize',None,6600)])
  add('InstallUISequence',prefix+[('Welcome','NOT Installed',1200),('Maintenance','Installed',1201),('ExecuteAction',None,1300),('Finished',None,-1),('Cancelled',None,-2),('FatalError',None,-3)])
  db.Commit();db=None
 meta={'versao_msi':version,'candidato':'3.0.0' if version=='3.0.0' else 'fixture','product_code':product,'upgrade_code':UPGRADE,'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'arquivos':hashes,'falha_injetada':fault,'assinatura_authenticode':False,'per_usuario':True,'bytes':out.stat().st_size}
 out.with_suffix('.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 return meta
if __name__=='__main__':
 import sys
 build(sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4],len(sys.argv)>5 and sys.argv[5]=='--falha-teste')
