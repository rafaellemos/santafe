#include "lua.h"
#include "lauxlib.h"
int luaopen_ensaio(lua_State *L) {
    luaL_checkversion(L);
    lua_pushboolean(L, 1);
    return 1;
}

#if defined(SANTAFE_DADOS_EXPERIMENTAL)
SANTAFE_MODULE_ABI;
#endif
