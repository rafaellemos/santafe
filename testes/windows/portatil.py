"""Assemble and exercise an isolated portable candidate; never install globally."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,zipfile
from licencas import prepare as prepare_notices, verify_archive, record_dependencies

def prepare(root,out,run):
 dest=out/'portatil-ação';bindir=dest/'bin';bindir.mkdir(parents=True)
 for name in ('santafe.exe','santafec.exe','santafe-sls.exe'):
  shutil.copyfile(root/'src'/name,bindir/name)
 for p in (root/'src').glob('*.dll'):shutil.copyfile(p,bindir/p.name)
 share=dest/'share/santafé/3.0/ferramentas';share.mkdir(parents=True)
 for tool in ('sls','pacotes'):
  target=share/tool;target.mkdir()
  for p in (root/'ferramentas'/tool).iterdir():
   if p.suffix in ('.fé','.json','.dll'):shutil.copyfile(p,target/p.name)
 headers=dest/'include';headers.mkdir()
 for name in ('lua.h','luaconf.h','lauxlib.h','lualib.h'):shutil.copyfile(root/'src'/name,headers/name)
 (dest/'lib').mkdir();shutil.copyfile(root/'src/libsantafe-3.dll.a',dest/'lib/libsantafe-3.dll.a')
 # Preserve third-party license notices delivered by the compiler's registry.
 compiler=Path(shutil.which('gcc')).resolve();licenses=compiler.parent.parent/'share/licenses'
 assert licenses.is_dir(),licenses
 shutil.copytree(licenses,dest/'LICENCAS-TERCEIROS')
 prepare_notices(root,dest)
 record_dependencies(dest,compiler)
 from dependencias import prepare as prepare_dependencies
 prepare_dependencies(dest)
 for name in ('LICENSE','COPYRIGHT'):
  if (root/name).is_file():shutil.copyfile(root/name,dest/name)
 (dest/'LEIA-ME.txt').write_text('Santafé 3.0.0 — Windows x64; SLS 1.1.0 e gerenciador 1.1.0.\nNúcleo, SLS e gerenciador local. Executar bin/santafe.exe ou bin/santafe-sls.exe.\nO ZIP portátil não modifica PATH ou registro. O MSI acrescenta bin ao PATH do usuário.\nNenhuma modalidade instala serviços. Instalador sem assinatura Authenticode; confira a origem e o SHA-256 no portal oficial.\nNTFS local; UNC, junções e links recusados nas ferramentas protegidas.\nBibliotecas C requerem GCC UCRT64 confiável em SANTAFE_CC e --permitir-nativo.\nWindows 10/11: validação visual do candidato com o mesmo código; a identidade final e o instalador têm testes próprios registrados.\nInstalador MSI: veja o resultado da bateria separada na entrega.\nCompilador/terceiros: https://packages.msys2.org/ ; fontes: https://repo.msys2.org/mingw/sources/\n',encoding='utf-8')
 env={k:v for k,v in os.environ.items() if k.upper() in ('SYSTEMROOT','WINDIR','TEMP','TMP','USERPROFILE')}
 env['PATH']=str(Path(os.environ['SYSTEMROOT'])/'System32')
 work=out/'portatil-projeto';work.mkdir()
 exe=bindir/'santafe.exe'
 run('portatil-versao',[exe,'-v'],work,env=env)
 run('portatil-ajuda',[exe,'instale','--ajuda'],work,env=env)
 run('portatil-instalar-fe',[exe,'instale','exemplo','1.0.0','--repositorio-local',out/'casos/repo'],work,env=env)
 run('portatil-importar-fe',[exe,'-e','garanta((importe "exemplo").valor==42)'],work,env=env)
 run('portatil-sls',[Path(os.sys.executable),Path(__file__).parent/'portatil_sls.py',root,bindir/'santafe-sls.exe',out/'portatil-sls.json'],timeout=240,env=env)
 native=share/'sls/nativo.dll';hidden=native.with_suffix('.ausente');native.rename(hidden)
 try:run('sls-recusa-sem-protecao',[bindir/'santafe-sls.exe'],work,expected=None,env=env)
 finally:hidden.rename(native)
 # Relocate once more; tools must find their own installation, not PATH or CWD.
 renamed=out/'portatil-renomeado';dest.rename(renamed);dest=renamed
 run('portatil-realocado',[dest/'bin/santafe.exe','instale','--ajuda'],work,env=env)
 manifest={str(p.relative_to(dest)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(dest.rglob('*')) if p.is_file()}
 (dest/'SHA256.json').write_text(json.dumps(manifest,ensure_ascii=True,indent=2)+'\n',encoding='utf-8')
 archive=out/'santafe-3.0.0-windows-x64-portatil.zip'
 with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
  for p in sorted(dest.rglob('*')):
   if p.is_file():z.write(p,str(p.relative_to(dest)).replace('\\','/'))
 assert verify_archive(archive)==6
 from dependencias import verify_package
 with zipfile.ZipFile(archive) as z:assert verify_package(z.read)==4
 run('fontes-e-dependencias',[Path(os.sys.executable),Path(__file__).parent/'testar-dependencias.py',archive,out/'dependencias.json'])
 run('avisos-redistribuicao',[Path(os.sys.executable),Path(__file__).parent/'testar-licencas.py',root,out/'licencas.json'])
 (out/'portatil.json').write_text(json.dumps({'arquivo':archive.name,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'bytes':archive.stat().st_size,'arquivos':len(manifest),'sistema':'WindowsServer2022-x64','producao_alterada':False,'instalacao_global':False,'versao_estavel':True},indent=2)+'\n',encoding='utf-8')
