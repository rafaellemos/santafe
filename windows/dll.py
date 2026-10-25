"""Ensaio isolado da IBA dinâmica Windows; não é SDK instalado."""
from pathlib import Path
import json
import shutil

def test(cand, work, run, sf):
    src=cand/'src'; target=work/'dll';target.mkdir()
    library=target/'santafe-3.dll';imports=target/'libsantafe-3.dll.a'
    objects=[p for p in sorted(src.glob('*.o')) if p.name not in ('santafe.o','santafec.o','santafe-windows.o')]
    if len(objects)<30:raise RuntimeError('objetos do núcleo ausentes')
    run('dll-nucleo',['gcc','-shared','-Wl,--export-all-symbols',
        '-Wl,--out-implib,'+str(imports),*objects,'-lm','-lws2_32','-o',library],cand)
    exe=target/'santafe-dll.exe'
    run('dll-interpretador',['gcc',src/'santafe.o',src/'santafe-windows.o',imports,
        '-lm','-lws2_32','-o',exe],cand)
    sf('dll-listas','garanta(json.cod([nulo,{}])=="[null,{}]")',exe,cand)
    mods=target/'módulos-漢字';mods.mkdir()
    for name,descriptor,accepted in [
        ('atual','SANTAFE_MODULE_ABI;',True),
        ('legado','',False),
        ('epoca_errada','#undef SANTAFE_ABI_MAJOR\n#define SANTAFE_ABI_MAJOR 2\nSANTAFE_MODULE_ABI;',False),
        ('curto','SANTAFE_ABI_EXPORT const uint32_t santafe_module_abi[2]={0x53464942u,2};',False)]:
        # O linker MinGW deste executor não aceita saída em caminho Unicode.
        # Compilar em ASCII e copiar preserva o teste real do carregador Santafé.
        code=target/(name+'.c');built=target/(name+'.dll');binary=mods/(name+'.dll')
        code.write_text('#include "lua.h"\n#include "lauxlib.h"\n'+descriptor+'''
__declspec(dllexport) int luaopen_ensaio(lua_State *L) {
  luaL_checkversion(L);
  lua_createlist(L,1);lua_pushnil(L);lua_rawseti(L,-2,1);return 1;
}
''',encoding='utf-8')
        run('dll-compilar-'+name,['gcc','-shared','-DSANTAFE_DADOS_EXPERIMENTAL',
            '-I'+str(src),code,imports,'-o',built],cand)
        shutil.copyfile(built,binary)
        path=json.dumps(binary.as_posix(),ensure_ascii=False)
        probe='local f,erro=módulo.carregarBib('+path+',"luaopen_ensaio"); '
        probe+=('garanta(f,erro);local l=f();garanta(tipo(l)=="lista" e #l==1 e tabela.temChave(l,1));'
                if accepted else 'garanta(f==nulo e erro:procure("IBA incompativel",1,verdadeiro),erro);')
        # Repetir na mesma VM cobre também a tabela de DLLs já carregadas.
        sf('dll-conferir-'+name,probe+'\n'+probe,exe,cand)
