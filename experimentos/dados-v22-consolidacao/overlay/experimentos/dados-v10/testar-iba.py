#!/usr/bin/env python3
"""IBA/bytecode: recusa antecipada, SDK instalado e compilação de módulos."""
from pathlib import Path
import hashlib,json,os,platform,shlex,subprocess,sys,tempfile
R=Path(__file__).resolve().parents[2]
if not (R/'.laboratorio-dados10').is_file():raise SystemExit('somente laboratório dados.10')
B=R/'src/santafé'; C=R/'src/santafec'; results=[]
P=Path(tempfile.mkdtemp(prefix='santafe-iba10-',dir='/tmp'))
def run(args,ok=True):
 p=subprocess.run([str(x) for x in args],capture_output=True,text=True,timeout=30)
 if ok and p.returncode:raise RuntimeError(str(args)+'\n'+p.stdout+p.stderr)
 return p
def sf(code):return run([B,'-E','-P','-e',code])
def passed(s):results.append(s);print('PASSOU',s,flush=True)
def module(name,descriptor,check=False,flags=()):
 c=P/(name+'.c');lib=P/(name+'.so')
 c.write_text('#include "lua.h"\n#include "lauxlib.h"\n'+descriptor+'\n#if defined(__GNUC__)\n__attribute__((visibility("default")))\n#endif\nint luaopen_ensaio(lua_State *L) {'+('luaL_checkversion(L);' if check else '')+' lua_pushinteger(L, 42); return 1;}\n')
 cmd=['cc','-fPIC','-DSANTAFE_DADOS_EXPERIMENTAL','-I'+str(R/'src'),*flags,str(c),'-o',str(lib)]
 cmd+=['-bundle','-undefined','dynamic_lookup'] if platform.system()=='Darwin' else ['-shared']
 run(cmd);return lib
try:
 for name,desc,accepted,check in (
 ('atual','SANTAFE_MODULE_ABI;',True,True),
 ('sem_checkversion','SANTAFE_MODULE_ABI;',True,False),
 ('legado_sem_checkversion','',False,False),
 ('legado_com_checkversion','',False,True),
 ('epoca_errada','#undef SANTAFE_ABI_MAJOR\n#define SANTAFE_ABI_MAJOR 2\nSANTAFE_MODULE_ABI;',False,False),
 ('numero_errado','#undef LUA_FLOAT_TYPE\n#define LUA_FLOAT_TYPE 999\nSANTAFE_MODULE_ABI;',False,False),
 ('descritor_curto','SANTAFE_ABI_EXPORT const uint32_t santafe_module_abi[2]={0x53464942u,2};',False,False)):
  lib=module(name,desc,check);q=json.dumps(str(lib),ensure_ascii=False)
  body='local f,falha=módulo.carregarBib('+q+',"luaopen_ensaio"); '
  body+=('garanta(f,falha); garanta(f()==42);' if accepted else 'garanta(f==nulo e falha:procure("IBA incompativel",1,verdadeiro),falha);')
  body+=' garanta(json.cod([nulo])=="[null]")'
  sf(body)
  # Cached and global-only paths must enforce the same contract.
  sf(body+'; '+body)
  sf('local f,falha=módulo.carregarBib('+q+',"*"); '+('garanta(f==verdadeiro,falha)' if accepted else 'garanta(f==nulo e falha:procure("IBA incompativel",1,verdadeiro))'))
  passed('módulo '+name+': carga, repetição e símbolos globais')
 lib=module('oculto','SANTAFE_MODULE_ABI;',False,['-fvisibility=hidden'])
 sf('local f,falha=módulo.carregarBib('+json.dumps(str(lib),ensure_ascii=False)+',"luaopen_ensaio"); garanta(f,falha); garanta(f()==42)')
 passed('descritor exportado mesmo com visibilidade oculta')
 # Build using only the installed public SDK and pkg-config; source headers must
 # not leak into the compile. Spaces in the prefix exercise generated quoting.
 sdk=P/'SDK com espaços';plat='macosx' if platform.system()=='Darwin' else 'linux'
 for part in ('bin','pc'):
  run(['bash',R/'ferramentas/instalar-arquivos.sh',part,sdk,plat,'0.0.0-dados.10'])
 env=dict(os.environ,PKG_CONFIG_PATH=str(sdk/'lib/pkgconfig'))
 pc=subprocess.check_output(['pkg-config','--cflags','santafe'],env=env)
 # pkgconf Debian escapa octetos UTF-8 individualmente. Desfazer o quoting
 # em octetos antes de decodificar, sem executar a saída como shell.
 cflags=[os.fsdecode(x.encode('latin1')) for x in shlex.split(pc.decode('latin1'))];assert '-DSANTAFE_DADOS_EXPERIMENTAL' in cflags
 for language,compiler,suffix in (('C','cc','.c'),('C++','c++','.cpp')):
  source=P/('sdk'+suffix);lib=P/('sdk-'+compiler.replace('+','p')+'.so')
  source.write_text('#include "lua.hpp"\nSANTAFE_MODULE_ABI;\nextern "C" int luaopen_ensaio(lua_State *L){luaL_checkversion(L);lua_createlist(L,1);lua_pushnil(L);lua_rawseti(L,-2,1);return 1;}\n' if language=='C++' else '#include "lua.h"\n#include "lauxlib.h"\nSANTAFE_MODULE_ABI;\nint luaopen_ensaio(lua_State *L){luaL_checkversion(L);lua_createlist(L,1);lua_pushnil(L);lua_rawseti(L,-2,1);return 1;}\n')
  cmd=[compiler,'-fPIC',*cflags,str(source),'-o',str(lib)]
  cmd+=['-bundle','-undefined','dynamic_lookup'] if plat=='macosx' else ['-shared']
  run(cmd)
  run([sdk/'bin/santafé','-E','-P','-e','local f,falha=módulo.carregarBib('+json.dumps(str(lib),ensure_ascii=False)+',"luaopen_ensaio"); garanta(f,falha); local l=f(); garanta(tipo(l)=="lista" e #l==1 e tabela.temChave(l,1) e l[1]==nulo)'])
  passed('SDK instalado '+language+': pkg-config, IBA3, lista e nulo')

 src=P/'caso.fé';binary=P/'caso.bin'
 src.write_text('local f=função(x) retorne [x,nulo,{campo=nulo},[1,2]], [=[ação ®literal]=] fim\nlocal a,b=f(7); garanta(#a==4 e tabela.temChave(a[3],"campo") e tipo(a[4])=="lista" e b=="ação ®literal"); mostre("BYTECODE3_OK")')
 for flags in ([],['-s']):
  run([C,*flags,'-o',binary,src]);data=binary.read_bytes();assert data[:6]==b'\x1bSF3\x30\0'
  assert 'BYTECODE3_OK' in run([B,'-E','-P',binary]).stdout
 passed('bytecode normal e sem depuração: listas/nulo/gabarito bruto preservados')
 data=binary.read_bytes()
 for name,blob in [('versao',data[:4]+b'\x10'+data[5:]),('formato',data[:5]+b'\x01'+data[6:]),('dados9',b'\x1bSFD'+data[4:]),('lua',b'\x1bLua'+data[4:])]+[('truncado'+str(n),data[:n]) for n in range(1,33)]:
  bad=P/(name+'.bin');bad.write_bytes(blob)
  p=run([B,'-E','-P',bad],False);assert p.returncode>0 and p.returncode<128,(name,p)
 passed('36 cabeçalhos antigos/corrompidos/truncados recusados sem sinal')
 stable=Path(os.environ['SANTAFE_ESTAVEL']);old=P/'estavel.bin'
 run([stable,'-E','-P','-e','local f=garanta(es.abra('+json.dumps(str(old),ensure_ascii=False)+',"wb")); f:escreva(colar.binário(função() retorne 7 fim)); f:feche()'])
 assert run([B,'-E','-P',old],False).returncode==1
 assert run([stable,'-E','-P',binary],False).returncode==1
 passed('bytecode 2.1 e IBA3 recusados reciprocamente')
 # Public project ABI fingerprint cannot reuse native objects from dados.9.
 sf('local N=garanta(módulo.carregarBib('+json.dumps(str(R/'ferramentas/pacotes/nativo.so'),ensure_ascii=False)+',"luaopen_pacotes_nativo"))(); local p=N.plataforma(); garanta(p.iba=="santafe-3" e p.bytecode==48 e p.abiDados>0x300000)')
 passed('identidade nativa do gerenciador inclui IBA e bytecode')
finally:
 (R/'evidencias').mkdir(exist_ok=True)
 (R/'evidencias/iba10.json').write_text(json.dumps({'passaram':results,'esperados':14,'laboratorio':str(P)},ensure_ascii=False,indent=2)+'\n')
