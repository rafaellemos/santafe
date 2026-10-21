/* Fault injection around the real lexer and POSIX indexer. No user data. */
#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "lua.h"
#include "lauxlib.h"
#include "lualib.h"
extern int luaopen_sls_nativo(lua_State *L);
typedef struct { long remaining; size_t bytes; } Alloc;
static void *allocate(void *ud, void *ptr, size_t old, size_t size) {
    Alloc *a=ud; void *next;
    if (!ptr) old=0;
    if (!size) { free(ptr); a->bytes-=old; return NULL; }
    if (size>old && a->remaining>=0) {
        if (!a->remaining) return NULL;
        a->remaining--;
    }
    next=realloc(ptr,size);
    if (next) a->bytes=a->bytes-old+size;
    return next;
}
static int descriptors(void) {
    int count=0, fd;
    for (fd=0;fd<1024;fd++) if (fcntl(fd,F_GETFD)!=-1) count++;
    return count;
}
static void lexical(lua_State *L,const char *data,size_t size) {
    lua_getglobal(L,"depure"); lua_getfield(L,-1,"lexemas"); lua_remove(L,-2);
    lua_pushlstring(L,data,size);
}
int main(int argc,char **argv) {
    const char *source="local vari\xc3\xa1vel=1; mostre(`\xc2\xaevari\xc3\xa1vel \xe2\x93\x87{vari\xc3\xa1vel+2}`)";
    int mode,threshold,baseline=descriptors();
    assert(argc==2);
    for (mode=0;mode<3;mode++) for (threshold=0;threshold<300;threshold++) {
        Alloc a={-1,0}; lua_State *L=lua_newstate(allocate,&a); int status,args=1;
        assert(L); luaL_openlibs(L);
        if (mode==0) lexical(L,source,strlen(source));
        else {
            luaL_requiref(L,"sls_nativo",luaopen_sls_nativo,1); lua_pop(L,1);
            lua_getglobal(L,"sls_nativo"); lua_getfield(L,-1,"abraRaiz");
            lua_pushstring(L,argv[1]); assert(lua_pcall(L,1,1,0)==LUA_OK);
            assert(lua_isuserdata(L,-1)); lua_setglobal(L,"root"); lua_pop(L,1);
            lua_getglobal(L,"sls_nativo"); lua_getfield(L,-1,mode==1?"listeFontes":"leiaFonte"); lua_remove(L,-2);
            lua_getglobal(L,"root");
            if (mode==2) { lua_pushliteral(L,"teste.fé"); args=2; }
        }
        a.remaining=threshold;
        status=lua_pcall(L,args,LUA_MULTRET,0);
        a.remaining=-1;
        if (status!=LUA_OK && status!=LUA_ERRMEM)
            fprintf(stderr,"mode=%d threshold=%d status=%d error=%s\n",mode,threshold,status,lua_tostring(L,-1));
        assert(status==LUA_OK || status==LUA_ERRMEM);
        lua_settop(L,0); lua_gc(L,LUA_GCCOLLECT,0); lua_close(L);
        assert(a.bytes==0); assert(descriptors()==baseline);
    }
    {
        Alloc a={-1,0}; lua_State *L=lua_newstate(allocate,&a); unsigned state=42; int i,j;
        assert(L); luaL_openlibs(L);
        for (i=0;i<3000;i++) {
            char data[512]; size_t n=(size_t)(i%512);
            for (j=0;j<(int)n;j++) { state=1664525*state+1013904223; data[j]=(char)(state>>24); }
            lexical(L,data,n); assert(lua_pcall(L,1,LUA_MULTRET,0)==LUA_OK);
            assert(lua_istable(L,1));
            for (j=1;j<=(int)lua_rawlen(L,1);j++) {
                lua_Integer start,end;
                lua_rawgeti(L,1,j); lua_getfield(L,-1,"início"); start=lua_tointeger(L,-1); lua_pop(L,1);
                lua_getfield(L,-1,"fim"); end=lua_tointeger(L,-1); lua_pop(L,2);
                assert(start>=0 && end>=start && (size_t)end<=n);
            }
            lua_settop(L,0);
            if (i%50==0) lua_gc(L,LUA_GCCOLLECT,0);
        }
        lua_close(L); assert(a.bytes==0);
    }
    puts("Lexer e suporte SLS: 900 falhas de alocação, 3000 entradas arbitrárias, heap e descritores: ok");
    return 0;
}
