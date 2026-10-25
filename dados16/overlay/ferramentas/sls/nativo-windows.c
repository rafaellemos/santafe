/* Windows SLS: bounded reads only, never executes workspace code. */
#include "../windows/arquivos.h"
#include <io.h>
#include <fcntl.h>
#include <bcrypt.h>
#ifdef SANTAFE_DADOS_EXPERIMENTAL
SANTAFE_MODULE_ABI;
#endif
#define SEARCH_MT "SLS.Win32.busca"
typedef struct { HANDLE h; } Search;
static int close_search(lua_State *L){Search *s=lua_touserdata(L,1);if(s->h!=INVALID_HANDLE_VALUE)FindClose(s->h);s->h=INVALID_HANDLE_VALUE;return 0;}
static int root(lua_State *L) {
    size_t n;const char *p=luaL_checklstring(L,1,&n);WF *w=wf_new(L);
    if(!wf_root(w,p,n)){wf_close(w);return wf_fail(L,"raiz inacessivel ou insegura");}return 1;
}
static int read_source(lua_State *L) {
    WF *w=luaL_checkudata(L,1,WF_MT);size_t n;const char *p=luaL_checklstring(L,2,&n);
    lua_Integer max=luaL_optinteger(L,3,4*1024*1024);
    luaL_argcheck(L,max>0&&max<=16*1024*1024,3,"limite invalido");return wf_read(L,w,p,n,(size_t)max);
}
typedef struct{int files,entries,dirs;const char *problem;} Scan;
static void scan(lua_State *L,WF *root,const char *prefix,int output,Scan *s,int depth) {
    WIN32_FIND_DATAW item;wchar_t pattern[WF_MAX];Search *search;int top=lua_gettop(L);
    if(depth>32||++s->dirs>1024){s->problem="limite de diretorios";return;}
    luaL_checkstack(L,12,"profundidade de indexacao");
    if(wcslen(root->path)+3>=WF_MAX){s->problem="caminho excessivo";return;}
    wcscpy(pattern,root->path);wcscat(pattern,L"\\*");
    search=lua_newuserdata(L,sizeof(*search));search->h=INVALID_HANDLE_VALUE;
    luaL_getmetatable(L,SEARCH_MT);lua_setmetatable(L,-2);
    search->h=FindFirstFileW(pattern,&item);
    if(search->h==INVALID_HANDLE_VALUE){s->problem="diretorio ilegivel";lua_settop(L,top);return;}
    do {
        char name[1024],path[4096];size_t len;WF *child;
        if(++s->entries>20000){s->problem="limite de entradas";break;}
        if(item.cFileName[0]==L'.'||(item.dwFileAttributes&FILE_ATTRIBUTE_REPARSE_POINT))continue;
        if(!wf_component(item.cFileName,wcslen(item.cFileName))||!wf_utf8(item.cFileName,name,sizeof(name)))continue;
        if(strlen(prefix)+strlen(name)+2>=sizeof(path)){s->problem="caminho excessivo";break;}
        strcpy(path,prefix);strcat(path,name);len=strlen(path);
        if(item.dwFileAttributes&FILE_ATTRIBUTE_DIRECTORY) {
            if(!strcmp(name,"node_modules")||!strcmp(name,"dist")||!strcmp(name,"build")||!strcmp(name,"construcao"))continue;
            child=wf_new(L);
            if(!wf_copy(child,root)||!wf_append(child,item.cFileName,wcslen(item.cFileName))||
               !wf_add(child,wf_open(child->path,FILE_LIST_DIRECTORY,FILE_SHARE_READ,OPEN_EXISTING,1,0))) {
                wf_close(child);lua_pop(L,1);s->problem="diretorio alterado ou inseguro";break;
            }
            strcat(path,"/");scan(L,child,path,output,s,depth+1);wf_close(child);lua_pop(L,1);
        } else if((len>=3&&!strcmp(path+len-3,".fe"))||(len>=4&&!strcmp(path+len-4,".f\xc3\xa9"))) {
            if(s->files>=512){s->problem="limite de 512 fontes";break;}
            lua_pushstring(L,path);lua_rawseti(L,output,++s->files);
        }
        if(s->problem)break;
    }while(FindNextFileW(search->h,&item));
    if(!s->problem && GetLastError()!=ERROR_NO_MORE_FILES)s->problem="leitura de diretorio falhou";
    FindClose(search->h);search->h=INVALID_HANDLE_VALUE;lua_settop(L,top);
}
static int sources(lua_State *L){WF *w=luaL_checkudata(L,1,WF_MT);Scan s={0,0,0,NULL};lua_newtable(L);scan(L,w,"",lua_gettop(L),&s,0);if(s.problem)lua_pushstring(L,s.problem);else lua_pushnil(L);return 2;}
static int ready(lua_State *L) {
    int ms=(int)luaL_optinteger(L,1,0);HANDLE h=GetStdHandle(STD_INPUT_HANDLE);DWORD type=GetFileType(h),n=0;ULONGLONG end;
    luaL_argcheck(L,ms>=0&&ms<=1000,1,"prazo invalido");end=GetTickCount64()+ms;
    if(type!=FILE_TYPE_PIPE&&type!=FILE_TYPE_DISK)return luaL_error(L,"SLS exige stdin canal ou arquivo");
    if(type==FILE_TYPE_DISK){lua_pushboolean(L,1);return 1;}
    do {
        if(!PeekNamedPipe(h,NULL,0,NULL,&n,NULL)) {
            if(GetLastError()==ERROR_BROKEN_PIPE){lua_pushboolean(L,1);return 1;}
            return luaL_error(L,"consulta do canal falhou");
        }
        if(n||GetTickCount64()>=end)break;Sleep(1);
    }while(1);
    lua_pushboolean(L,n>0);return 1;
}
static int input(lua_State *L){char b[65536];DWORD n;if(!ReadFile(GetStdHandle(STD_INPUT_HANDLE),b,sizeof(b),&n,NULL)){if(GetLastError()!=ERROR_BROKEN_PIPE)return luaL_error(L,"leitura stdin falhou");n=0;}if(n)lua_pushlstring(L,b,n);else lua_pushnil(L);return 1;}
static int protected_request(lua_State *L){int status,n=lua_gettop(L);luaL_checktype(L,1,LUA_TFUNCTION);status=lua_pcall(L,n-1,LUA_MULTRET,0);lua_sethook(L,NULL,0,0);n=lua_gettop(L);lua_pushboolean(L,status==LUA_OK);lua_insert(L,1);return n+1;}
static int hash_source(lua_State *L){size_t n,i;const char *p=luaL_checklstring(L,1,&n);unsigned char digest[32];char hex[65];BCRYPT_ALG_HANDLE a;NTSTATUS s;
 luaL_argcheck(L,n<=16*1024*1024,1,"fonte excessiva");s=BCryptOpenAlgorithmProvider(&a,BCRYPT_SHA256_ALGORITHM,NULL,0);if(s<0)return luaL_error(L,"SHA256 indisponivel");
 s=BCryptHash(a,NULL,0,(PUCHAR)p,(ULONG)n,digest,32);BCryptCloseAlgorithmProvider(a,0);if(s<0)return luaL_error(L,"SHA256 falhou");
 for(i=0;i<32;i++)sprintf(hex+2*i,"%02x",digest[i]);lua_pushlstring(L,hex,64);return 1;}
__declspec(dllexport) int luaopen_sls_nativo(lua_State *L){
 const luaL_Reg api[]={{"abraRaiz",root},{"leiaFonte",read_source},{"listeFontes",sources},{"entradaPronta",ready},{"leiaEntrada",input},{"executeProtegido",protected_request},{"sha256",hash_source},{NULL,NULL}};
 wf_register(L);if(luaL_newmetatable(L,SEARCH_MT)){lua_pushcfunction(L,close_search);lua_setfield(L,-2,LUA_MM_FINALIZE);}lua_pop(L,1);
 /* LSP Content-Length counts octets. CRT must not rewrite LF to CRLF. */
 _setmode(_fileno(stdin),_O_BINARY);_setmode(_fileno(stdout),_O_BINARY);
 luaL_newlib(L,api);return 1;
}
