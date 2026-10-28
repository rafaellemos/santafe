#!/usr/bin/env python3
"""Revisão IBA3 somente na árvore candidata fornecida."""
from pathlib import Path
import sys
s=Path(sys.argv[1]).resolve()
if not (s/'.laboratorio-dados10').is_file(): raise SystemExit('Exige laboratório dados.10')
def change(name,old,new,count=1):
 p=s/name;t=p.read_text()
 if t.count(old)!=count:raise RuntimeError((name,t.count(old),old[:100]))
 p.write_text(t.replace(old,new))
header='''/* IBA da próxima versão maior. LUA_VERSION_NUM é vocabulário herdado,
** não promessa de compatibilidade binária. Estados/objetos internos são opacos.
** Cada DSO deve declarar SANTAFE_MODULE_ABI em UMA unidade de tradução.
** O carregador valida o descritor antes de devolver/chamar luaopen_*.
** Isto não é sandbox: dlopen pode executar construtores da biblioteca. */
#ifdef SANTAFE_DADOS_EXPERIMENTAL
#include <stdint.h>
#define SANTAFE_ABI_MAJOR 3
#define SANTAFE_ABI_ID "santafe-3"
#define SANTAFE_BYTECODE_VERSION 0x30
#if defined(_WIN32)
#define SANTAFE_ABI_EXPORT __declspec(dllexport)
#elif defined(__GNUC__)
#define SANTAFE_ABI_EXPORT __attribute__((visibility("default")))
#else
#define SANTAFE_ABI_EXPORT
#endif
#define SANTAFE_ABI_DESCRIPTOR {0x53464942u, 10, SANTAFE_ABI_MAJOR, \\
 sizeof(void*), sizeof(lua_Integer), sizeof(lua_Number), LUA_INT_TYPE, \\
 LUA_FLOAT_TYPE, LUA_EXTRASPACE, LUAI_MAXSTACK}
#ifdef __cplusplus
#define SANTAFE_ABI_LINKAGE extern "C"
#else
#define SANTAFE_ABI_LINKAGE
#endif
#define SANTAFE_MODULE_ABI SANTAFE_ABI_LINKAGE SANTAFE_ABI_EXPORT const uint32_t santafe_module_abi[10] = SANTAFE_ABI_DESCRIPTOR
#endif

'''
change('src/lua.h','/*\n** Vocabulário público',header+'/*\n** Vocabulário público')
change('src/lua.h','#define LUA_SIGNATURE "\\x1bSFD"','#define LUA_SIGNATURE "\\x1bSF3"')
change('src/lauxlib.h','0x100000 + sizeof(lua_Integer)*16','0x300000 + sizeof(lua_Integer)*16')
change('src/lauxlib.h','/* Lists and stored null change the C contract even though the numeric types\n** still match Lua 5.3. Refuse old modules that use luaL_checkversion/newlib.\n** This is an experimental ABI fence, not the final major-version ABI. */','/* IBA3: também recusa módulos ligados diretamente que chamam checkversion.\n** O carregador dinâmico exige o descritor de TODOS os módulos. */')
change('src/lauxlib.c','n\\xC3\\xBA" "cleo e bibliotecas tem tipos num\\xC3\\xA9ricos incompat\\xC3\\xADveis','IBA ou tipos numericos incompativeis entre nucleo e biblioteca')
change('src/lundump.h','#define LUAC_FORMAT\t0\t/* this is the official format */','#define LUAC_FORMAT\t0\t/* formato local, não portátil */\n#ifdef SANTAFE_DADOS_EXPERIMENTAL\n#undef LUAC_VERSION\n#define LUAC_VERSION SANTAFE_BYTECODE_VERSION\n#endif')
# A descriptor lookup independent of luaopen; no module function is called here.
check='''#ifdef SANTAFE_DADOS_EXPERIMENTAL
static int checkmoduleabi(lua_State *L, void *lib) {
  static const uint32_t expected[10] = SANTAFE_ABI_DESCRIPTOR;
  const uint32_t *descriptor = NULL;
#if defined(LUA_USE_DLOPEN)
  descriptor = (const uint32_t *)dlsym(lib, "santafe_module_abi");
#elif defined(LUA_DL_DLL)
  descriptor = (const uint32_t *)GetProcAddress((HMODULE)lib, "santafe_module_abi");
#endif
  if (descriptor == NULL || descriptor[0] != expected[0] ||
      descriptor[1] != expected[1] || memcmp(descriptor, expected, sizeof(expected))) {
    lua_pushliteral(L, "IBA incompativel: modulo exige recompilacao e descritor santafe-3");
    return 0;
  }
  return 1;
}
#endif

'''
change('src/loadlib.c',"/* error codes for 'lookforfunc' */",check+"/* error codes for 'lookforfunc' */")
change('src/loadlib.c','    addtoclib(L, path, reg);','''#ifdef SANTAFE_DADOS_EXPERIMENTAL
    if (!checkmoduleabi(L, reg)) { lsys_unloadlib(reg); return ERRLIB; }
#endif
    addtoclib(L, path, reg);''')
for name in ('bibs/bibc/arquivo/arquivo.c','bibs/bibc/rede/rede.c','bibs/bibc/segredo/segredo.c','bibs/bibc/mariadb/mariadb.c','bibs/bibc/tomada/luasocket.c','ferramentas/pacotes/nativo.c','ferramentas/sls/nativo.c','experimentos/dados-v3/ensaio-abi.c'):
 p=s/name;t=p.read_text();guard='defined(SANTAFE_DADOS_EXPERIMENTAL)'
 if name=='ferramentas/sls/nativo.c': guard+=' && !defined(SANTAFE_SLS_EMBUTIDO)'
 p.write_text(t+'\n#if '+guard+'\nSANTAFE_MODULE_ABI;\n#endif\n')
change('ferramentas/pacotes/nativo.c','    lua_pushinteger(L,LUAL_NUMSIZES); lua_setfield(L,-2,"abiDados");','''    lua_pushinteger(L,LUAL_NUMSIZES); lua_setfield(L,-2,"abiDados");
    lua_pushstring(L,SANTAFE_ABI_ID); lua_setfield(L,-2,"iba");
    lua_pushinteger(L,SANTAFE_BYTECODE_VERSION); lua_setfield(L,-2,"bytecode");''')
change('testes/integracao/testar_pacotes.py','static int f(lua_State*L){lua_pushinteger','''#ifdef SANTAFE_DADOS_EXPERIMENTAL\\nSANTAFE_MODULE_ABI;\\n#endif\\nstatic int f(lua_State*L){lua_pushinteger''')
# Old ABI regression now refuses at load-time, not only inside the initializer.
change('experimentos/dados-v3/testar-abi.py',"        source='local f=garanta(módulo.carregarBib('+json.dumps(str(lib))+',\"luaopen_ensaio\")); local ok,r=proteja(f); '\n        source+=('garanta(ok e r==verdadeiro)' if experimental else 'garanta(não ok e r:procure(\"incompat\",1,verdadeiro))')", "        source='local f,falha=módulo.carregarBib('+json.dumps(str(lib))+',\"luaopen_ensaio\"); '\n        source+=('garanta(f,falha); garanta(f()==verdadeiro)' if experimental else 'garanta(f==nulo e falha:procure(\"incompat\",1,verdadeiro))')")
change('ferramentas/instalar-arquivos.sh',"      printf '%s\\n' 'Libs: -L${libdir} -llua' 'Libs.private: -lm' 'Cflags: -I${includedir}'",'      printf \'%s\\n\' \'Libs: -L"${libdir}" -llua\' \'Libs.private: -lm\'\n      if [[ "$4" == *-dados.* ]]; then\n        printf \'%s\\n\' \'Cflags: -I"${includedir}" -DSANTAFE_DADOS_EXPERIMENTAL\'\n      else\n        printf \'%s\\n\' \'Cflags: -I"${includedir}"\'\n      fi')
change('experimentos/dados-v6/carga.py',"        events=[json.loads(x) for x in (lab.path/'correio.pulso').read_text().splitlines()]\n        limited=sum(e['nome']=='correio.imapConexãoLimitada' for e in events)\n        assert refused and limited>=refused, (refused,limited)","        # O fechamento TLS pode chegar antes de a escrita assíncrona do PULSO\n        # completar. Exigir os MESMOS eventos, com prazo limitado para persistir.\n        deadline=time.monotonic()+3\n        while True:\n            lines=(lab.path/'correio.pulso').read_text().split('\\n')[:-1]\n            events=[json.loads(x) for x in lines if x]\n            limited=sum(e['nome']=='correio.imapConexãoLimitada' for e in events)\n            if limited>=refused or time.monotonic()>=deadline:break\n            time.sleep(.02)\n        assert refused and limited>=refused, (refused,limited)\n        report['imap_eventos_limite_persistidos']=limited")
change('experimentos/dados-v6/carga.py',"report={'resultado':'PASSOU','segundos'","report={'resultado':'EM_ANDAMENTO','segundos'")
change('experimentos/dados-v6/carga.py','    finally:\n        stop.set();watcher.join()',"    except BaseException:\n        report['resultado']='FALHOU'\n        raise\n    else:\n        report['resultado']='PASSOU'\n    finally:\n        stop.set();watcher.join()")
change('experimentos/dados-v6/carga.py',"                now=time.monotonic(); assert http('/carteiro/entrada')[0]==200","                now=time.monotonic(); response=http('/carteiro/entrada')\n                if response[0]!=200:\n                    (lab.path/('http-falha-'+str(threading.get_ident())+'.html')).write_bytes(response[2])\n                    raise AssertionError(('HTTP carga',response[0],response[2].decode('utf-8','replace')[-5000:]))")
change('experimentos/dados-v6/carga.py','    begin=time.monotonic()',"    duration=int(os.environ.get('SANTAFE_CARGA_SEGUNDOS','60'))\n    assert 60<=duration<=600\n    begin=time.monotonic()")
change('experimentos/dados-v6/carga.py','while time.monotonic()-begin<60:','while time.monotonic()-begin<duration:')
print('IBA3_APLICADA',s)
