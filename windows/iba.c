#include "lua.h"
#include "lauxlib.h"
#include <stdio.h>
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"IBA linha %d\n",__LINE__); return 1; } } while(0)
int main(void) {
    lua_State *L = luaL_newstate();
    CHECK(L != NULL);
    CHECK(SANTAFE_ABI_MAJOR == 3);
    lua_createlist(L, 2);
    lua_pushnil(L); lua_rawseti(L, -2, 1);
    lua_pushinteger(L, 42); lua_rawseti(L, -2, 2);
    CHECK(lua_islist(L, -1) && lua_rawlen(L, -1) == 2);
    lua_pushinteger(L, 1); CHECK(lua_rawpresent(L, -2));
    lua_pushinteger(L, 1); CHECK(lua_rawdelete(L, -2));
    CHECK(lua_rawlen(L, -1) == 1);
    lua_rawgeti(L, -1, 1); CHECK(lua_tointeger(L, -1) == 42);
    lua_close(L);
    puts("IBA_ESTATICA_OK");
    return 0;
}
