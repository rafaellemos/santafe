/* Incluído por arquivo.c; operações antigas mantêm contrato e implementação. */
#include "atomico.h"
typedef struct {
    lua_State *L; int tratador, dado;
    char *caminho; unsigned char *conteudo; size_t tamanho;
    at_resultado resultado;
} at_tarefa;

static int at_empilhe(lua_State *L, at_resultado r) {
    if (!r.erro) { lua_pushboolean(L,1); lua_pushnil(L); }
    else {
        lua_pushnil(L);
        lua_pushfstring(L,"gravação atômica: %s: %s",r.etapa,g_strerror(r.erro));
    }
    lua_pushstring(L,at_estado(r)); return 3;
}
static int l_at_grave(lua_State *L) {
    luaL_checktype(L,1,LUA_TSTRING); luaL_checktype(L,2,LUA_TSTRING);
    size_t n, pn;
    const unsigned char *s=(const unsigned char *)luaL_checklstring(L,2,&n);
    const char *p=arq_valide_caminho(L,1,&pn);
    return at_empilhe(L,at_grave(p,s,n));
}
static void at_trabalhe(GTask *task,gpointer origem,gpointer dados,GCancellable *cancelavel) {
    at_tarefa *t=dados; (void)origem; (void)cancelavel;
    t->resultado=at_grave(t->caminho,t->conteudo,t->tamanho);
    g_task_return_boolean(task,TRUE);
}
static void at_conclua(GObject *origem,GAsyncResult *resultado,gpointer dados) {
    at_tarefa *t=dados; lua_State *L=t->L; int base=lua_gettop(L);
    (void)origem; (void)resultado;
    lua_rawgeti(L,LUA_REGISTRYINDEX,t->tratador);
    at_empilhe(L,t->resultado);
    if (t->dado==LUA_REFNIL) lua_pushnil(L);
    else lua_rawgeti(L,LUA_REGISTRYINDEX,t->dado);
    if (lua_pcall(L,4,0,0)!=LUA_OK) {
        const char *mensagem=lua_tostring(L,-1);
        g_printerr("[arquivo] tratador atômico: %s\n",mensagem?mensagem:"erro sem texto");
    }
    lua_settop(L,base);
    luaL_unref(L,LUA_REGISTRYINDEX,t->tratador); luaL_unref(L,LUA_REGISTRYINDEX,t->dado);
    g_free(t->caminho); g_free(t->conteudo); g_free(t);
}
static int l_at_grave_async(lua_State *L) {
    luaL_checktype(L,1,LUA_TSTRING); luaL_checktype(L,2,LUA_TSTRING);
    size_t n,pn; const unsigned char *s=(const unsigned char *)luaL_checklstring(L,2,&n);
    const char *p=arq_valide_caminho(L,1,&pn);
    luaL_checktype(L,3,LUA_TFUNCTION);
    at_tarefa *t=g_new0(at_tarefa,1); t->L=L;
    lua_pushvalue(L,3); t->tratador=luaL_ref(L,LUA_REGISTRYINDEX);
    if (lua_gettop(L)>=4) lua_pushvalue(L,4); else lua_pushnil(L);
    t->dado=luaL_ref(L,LUA_REGISTRYINDEX);
    t->caminho=g_strndup(p,pn); t->conteudo=g_malloc(n?n:1); t->tamanho=n;
    if (n) memcpy(t->conteudo,s,n);
    GTask *task=g_task_new(NULL,NULL,at_conclua,t);
    g_task_set_task_data(task,t,NULL); g_task_run_in_thread(task,at_trabalhe); g_object_unref(task);
    lua_pushboolean(L,1); return 1;
}
