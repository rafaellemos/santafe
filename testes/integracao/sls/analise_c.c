/* The diagnostic belongs to a load, including fragmented/reentrant readers. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "lua.h"
#include "lauxlib.h"

typedef struct Input {
  const char *text;
  size_t offset, chunk;
  int nested;
} Input;

static const char *read_chunk(lua_State *L, void *data, size_t *size) {
  Input *input = (Input *)data;
  const char *result = input->text + input->offset;
  if (input->nested) {
    lua_Diagnostic inner;
    Input child = {"local x = )", 0, 1, 0};
    int top = lua_gettop(L);
    input->nested = 0;
    assert(lua_loaddiagnostic(L, read_chunk, &child, "@inner", "t", &inner) == LUA_ERRSYNTAX);
    assert(inner.hasrange && inner.start == 10 && inner.end == 11);
    lua_settop(L, top);
  }
  *size = strlen(result);
  if (*size > input->chunk) *size = input->chunk;
  input->offset += *size;
  return *size ? result : NULL;
}

static void check(lua_State *L, const char *text, size_t chunk, int nested,
                  int status, size_t start, size_t end) {
  Input input = {text, 0, chunk, nested};
  lua_Diagnostic diagnostic = {999, 999, 1};
  int top = lua_gettop(L);
  assert(lua_loaddiagnostic(L, read_chunk, &input, "@outer", "t", &diagnostic) == status);
  assert(lua_gettop(L) == top + 1);
  assert(diagnostic.hasrange == (status == LUA_ERRSYNTAX));
  assert(diagnostic.start == start && diagnostic.end == end);
  lua_settop(L, top);
}

int main(void) {
  lua_State *L = luaL_newstate();
  const char *source = "local emoji = \"\xF0\x9F\x9F\xA2\"; local x = )";
  size_t i, length = strlen(source);
  assert(L);
  for (i = 1; i <= length; ++i) {
    check(L, source, i, 0, LUA_ERRSYNTAX, length - 1, length);
    check(L, source, i, 1, LUA_ERRSYNTAX, length - 1, length);
    check(L, "local x = 1", i, 1, LUA_OK, 0, 0);
    check(L, "local t = { a + ) }", i, 0, LUA_ERRSYNTAX, 16, 17);
  }
  check(L, "", 1, 1, LUA_OK, 0, 0);
  lua_close(L);
  puts("API de análise C: fragmentação UTF-8, lookahead, reentrância e pilha: ok");
  return 0;
}
