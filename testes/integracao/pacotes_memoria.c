#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include "lua.h"
#include "lauxlib.h"
#include "lualib.h"
extern int luaopen_pacotes_nativo(lua_State *L);
typedef struct { long remaining; size_t bytes; } Alloc;
static void *allocate(void *ud,void *p,size_t old,size_t size) {
    Alloc *a=ud; void *next; if(!p) old=0;
    if(!size) { free(p); a->bytes-=old; return NULL; }
    if(size>old && a->remaining>=0) { if(!a->remaining) return NULL; a->remaining--; }
    next=realloc(p,size); if(next) a->bytes=a->bytes-old+size; return next;
}
static int descriptors(void) { int n=0,fd; for(fd=0;fd<1024;fd++) if(fcntl(fd,F_GETFD)!=-1) n++; return n; }
int main(int argc,char **argv) {
    const char *cases[]={
        "retorne N.raiz(ROOT)",
        "local r=garanta(N.raiz(ROOT)); retorne r:leia('origem')",
        "local r=garanta(N.raiz(ROOT)); retorne r:liste()",
        "local r=garanta(N.raiz(ROOT)); garanta(r:trave()); retorne r:grave('novo','abc',verdadeiro)",
        "retorne N.sha256(('a'):replique(4096))",
        "retorne N.base64(('a'):replique(4096))",
        "retorne N.decodBase64(('YWJj'):replique(1000))",
        "retorne N.chaveCaminho('bibf/variavel.fe')",
        "local r=garanta(N.raiz(ROOT)); retorne r:execute({'/usr/bin/printf','ok'},2,64)"
    };
    int mode,threshold,base=descriptors(); assert(argc==2);
    for(mode=0;mode<(int)(sizeof(cases)/sizeof(cases[0]));mode++) for(threshold=0;threshold<160;threshold++) {
        Alloc a={-1,0}; lua_State *L=lua_newstate(allocate,&a); int status; assert(L);
        luaL_openlibs(L); luaL_requiref(L,"N",luaopen_pacotes_nativo,1); lua_pop(L,1);
        lua_pushstring(L,argv[1]); lua_setglobal(L,"ROOT");
        assert(luaL_loadstring(L,cases[mode])==LUA_OK);
        a.remaining=threshold; status=lua_pcall(L,0,LUA_MULTRET,0); a.remaining=-1;
        if(status!=LUA_OK && status!=LUA_ERRMEM) fprintf(stderr,"mode=%d threshold=%d status=%d %s\n",mode,threshold,status,lua_tostring(L,-1));
        assert(status==LUA_OK || status==LUA_ERRMEM);
        lua_settop(L,0); lua_gc(L,LUA_GCCOLLECT,0); lua_close(L);
        assert(a.bytes==0); assert(descriptors()==base);
    }
    puts("Pacotes nativo: 1440 falhas de alocacao; heap e descritores preservados: ok"); return 0;
}
