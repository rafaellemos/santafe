#include "lua.h"
#include "lauxlib.h"
#include "lualib.h"
#include <assert.h>
#include <stdio.h>

static int bad_pointer_write(lua_State *L) {
  lua_pushinteger(L,42);
  lua_rawsetp(L,1,(void *)L);
  return 0;
}
static int bad_raw_index(lua_State *L) { lua_rawgeti(L,1,0); return 1; }

int main(void) {
  lua_State *L=luaL_newstate(); assert(L);
  luaL_openlibs(L);
  lua_createlist(L,0); assert(lua_islist(L,1));
  lua_pushnil(L); lua_rawseti(L,1,1);
  assert(lua_rawlen(L,1)==1);
  lua_pushinteger(L,1); assert(lua_rawpresent(L,1));
  lua_rawgeti(L,1,1); assert(lua_isnil(L,-1)); lua_pop(L,1);
  lua_pushcfunction(L,bad_pointer_write); lua_pushvalue(L,1);
  assert(lua_pcall(L,1,0,0)!=LUA_OK); lua_pop(L,1);
  lua_pushcfunction(L,bad_raw_index); lua_pushvalue(L,1);
  assert(lua_pcall(L,1,0,0)!=LUA_OK); lua_pop(L,1);
  assert(lua_rawlen(L,1)==1);
  lua_pushinteger(L,1); assert(lua_rawdelete(L,1));
  assert(lua_rawlen(L,1)==0);
  lua_close(L);
  puts("API_C_DADOS_OK"); return 0;
}
