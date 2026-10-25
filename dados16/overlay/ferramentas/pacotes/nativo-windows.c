/* Private package I/O for Windows. No shell or inherited ambient credentials.
 * Filesystem capabilities in arquivos.h reject reparse points and hardlinks. */
#include "../windows/arquivos.h"
#include <glib.h>
#include <bcrypt.h>
#ifdef SANTAFE_DADOS_EXPERIMENTAL
SANTAFE_MODULE_ABI;
#endif
#define MEMORY "Pacotes.Win32.memoria"
#define MAX_BYTES (64*1024*1024)
typedef struct{void *p;}Memory;
static int gc_memory(lua_State *L){Memory *m=lua_touserdata(L,1);g_free(m->p);m->p=NULL;return 0;}
static Memory *memory(lua_State *L){Memory *m=lua_newuserdata(L,sizeof(*m));m->p=NULL;luaL_getmetatable(L,MEMORY);lua_setmetatable(L,-2);return m;}
static WF *root_arg(lua_State *L){WF *w=luaL_checkudata(L,1,WF_MT);luaL_argcheck(L,w->n>0,1,"raiz fechada");return w;}
static int valid_path(const char *s,size_t n){wchar_t p[WF_MAX];return wf_relative(s,n,p);}
static const char *path_arg(lua_State *L,int i,size_t *n){const char *p=luaL_checklstring(L,i,n);luaL_argcheck(L,valid_path(p,*n),i,"caminho relativo inseguro");return p;}
static int open_root(lua_State *L){size_t n;const char *p=luaL_checklstring(L,1,&n);WF *w=wf_new(L);if(!wf_root(w,p,n)){wf_close(w);return wf_fail(L,"raiz inacessivel ou insegura");}return 1;}
static int subroot(lua_State *L){WF *root=root_arg(L),*w;size_t n;const char *p=path_arg(L,2,&n);wchar_t rel[WF_MAX];wf_relative(p,n,rel);w=wf_new(L);if(!wf_copy(w,root)||!wf_walk(w,rel,0)){wf_close(w);return wf_fail(L,"subraiz insegura");}return 1;}
static int mkdirs(lua_State *L){WF *root=root_arg(L),*w;size_t n;const char *p=path_arg(L,2,&n);wchar_t rel[WF_MAX];wf_relative(p,n,rel);w=wf_new(L);if(!wf_copy(w,root)||!wf_walk(w,rel,1)){wf_close(w);return wf_fail(L,"criar diretorios");}wf_close(w);lua_pushboolean(L,1);return 1;}
static int read_file(lua_State *L){WF *root=root_arg(L);size_t n;const char *p=path_arg(L,2,&n);lua_Integer max=luaL_optinteger(L,3,MAX_BYTES);luaL_argcheck(L,max>0&&max<=MAX_BYTES,3,"limite invalido");return wf_read(L,root,p,n,max);}
static int exists(lua_State *L){WF *root=root_arg(L),*w;size_t n;const char *p=path_arg(L,2,&n);wchar_t leaf[256];HANDLE h;BY_HANDLE_FILE_INFORMATION st;
 w=wf_new(L);if(!wf_parent(w,root,p,n,leaf,0)||!wf_append(w,leaf,wcslen(leaf)))goto fail;
 h=wf_at(w->h[w->n-1],leaf,FILE_READ_ATTRIBUTES,FILE_SHARE_READ|FILE_SHARE_WRITE,OPEN_EXISTING,-1,1);
 if(h==INVALID_HANDLE_VALUE)goto fail;
 if(!GetFileInformationByHandle(h,&st)||GetFileType(h)!=FILE_TYPE_DISK||(st.dwFileAttributes&FILE_ATTRIBUTE_REPARSE_POINT)||(!(st.dwFileAttributes&FILE_ATTRIBUTE_DIRECTORY)&&st.nNumberOfLinks!=1)) {CloseHandle(h);wf_close(w);SetLastError(ERROR_ACCESS_DENIED);return wf_fail(L,"caminho especial");}
 CloseHandle(h);wf_close(w);lua_pushstring(L,(st.dwFileAttributes&FILE_ATTRIBUTE_DIRECTORY)?"diretorio":"arquivo");return 1;
fail:{DWORD e=GetLastError();wf_close(w);if(e==ERROR_FILE_NOT_FOUND||e==ERROR_PATH_NOT_FOUND){lua_pushboolean(L,0);return 1;}SetLastError(e);return wf_fail(L,"consultar caminho");}}
static int random_bytes(unsigned char *p,ULONG n){if(BCryptGenRandom(NULL,p,n,BCRYPT_USE_SYSTEM_PREFERRED_RNG)<0){SetLastError(ERROR_GEN_FAILURE);return 0;}return 1;}
static int write_file(lua_State *L){WF *root=root_arg(L),*w;size_t n,len,used=0;const char *p=path_arg(L,2,&len),*bytes=luaL_checklstring(L,3,&n);int replace=lua_toboolean(L,4);wchar_t leaf[256],tmp[80],dest[WF_MAX];HANDLE h=INVALID_HANDLE_VALUE;unsigned char rnd[16];unsigned i;DWORD wrote,error;FILE_RENAME_INFO *rename;size_t rename_size;FILE_DISPOSITION_INFO remove={TRUE};const char *stage="preparar escrita";
 luaL_argcheck(L,n<=MAX_BYTES,3,"arquivo excessivo");w=wf_new(L);
 if(!wf_parent(w,root,p,len,leaf,0))goto fail;
 wcscpy(dest,w->path);if(wcslen(dest)+wcslen(leaf)+2>=WF_MAX){SetLastError(ERROR_BUFFER_OVERFLOW);goto fail;}wcscat(dest,L"\\");wcscat(dest,leaf);
 /* Existing targets may be replaced atomically, never followed. Refuse special
  * targets explicitly; a racing replacement cannot redirect the rename. */
 {HANDLE target=wf_at(w->h[w->n-1],leaf,FILE_READ_ATTRIBUTES,FILE_SHARE_READ|FILE_SHARE_WRITE,OPEN_EXISTING,0,1);
  if(target!=INVALID_HANDLE_VALUE)CloseHandle(target);else if(GetLastError()!=ERROR_FILE_NOT_FOUND)goto fail;}
 if(!random_bytes(rnd,16))goto fail;
 wcscpy(tmp,L".escrita-");for(i=0;i<16;i++)swprintf(tmp+8+2*i,3,L"%02x",rnd[i]);
 if(!wf_append(w,tmp,wcslen(tmp)))goto fail;
 stage="criar temporario";h=wf_at(w->h[w->n-1],tmp,GENERIC_WRITE|DELETE,0,CREATE_NEW,0,1);if(h==INVALID_HANDLE_VALUE)goto fail;
 stage="escrever temporario";while(used<n){if(!WriteFile(h,bytes+used,(DWORD)(n-used),&wrote,NULL)||!wrote)goto fail;used+=wrote;}
 stage="sincronizar temporario";if(!FlushFileBuffers(h))goto fail;
 rename_size=offsetof(FILE_RENAME_INFO,FileName)+(wcslen(leaf)+1)*sizeof(wchar_t);
 rename=calloc(1,rename_size);if(!rename){SetLastError(ERROR_NOT_ENOUGH_MEMORY);goto fail;}
 rename->ReplaceIfExists=replace;rename->RootDirectory=w->h[w->n-1];rename->FileNameLength=(DWORD)(wcslen(leaf)*sizeof(wchar_t));memcpy(rename->FileName,leaf,rename->FileNameLength);
 stage="substituir por handle";if(!wf_rename(h,rename,(DWORD)rename_size)){error=GetLastError();free(rename);SetLastError(error);goto fail;}free(rename);
 CloseHandle(h);wf_close(w);lua_pushboolean(L,1);return 1;
fail:error=GetLastError();if(h!=INVALID_HANDLE_VALUE){SetFileInformationByHandle(h,FileDispositionInfo,&remove,sizeof(remove));CloseHandle(h);}wf_close(w);SetLastError(error);return wf_fail(L,stage);}
static int lock_root(lua_State *L){WF *root=root_arg(L),*w;wchar_t leaf[256];HANDLE h;OVERLAPPED o={0};
 luaL_argcheck(L,!root->lock,1,"raiz ja travada");w=wf_new(L);
 if(!wf_parent(w,root,".santafe/trava",14,leaf,1)||!wf_append(w,leaf,wcslen(leaf))){wf_close(w);return wf_fail(L,"diretorio da trava");}
 h=wf_at(w->h[w->n-1],leaf,GENERIC_READ|GENERIC_WRITE|READ_CONTROL,FILE_SHARE_READ|FILE_SHARE_WRITE,OPEN_ALWAYS,0,1);
 if(h==INVALID_HANDLE_VALUE){wf_close(w);return wf_fail(L,"abrir trava");}
 if(!wf_owner(h)||!LockFileEx(h,LOCKFILE_EXCLUSIVE_LOCK|LOCKFILE_FAIL_IMMEDIATELY,0,1,0,&o)){DWORD e=GetLastError();CloseHandle(h);wf_close(w);SetLastError(e);return wf_fail(L,"trava insegura ou instalacao em andamento");}
 if(!DuplicateHandle(GetCurrentProcess(),w->h[w->n-1],GetCurrentProcess(),&root->lock_parent,0,FALSE,DUPLICATE_SAME_ACCESS)){DWORD e=GetLastError();CloseHandle(h);wf_close(w);SetLastError(e);return wf_fail(L,"fixar diretorio da trava");}
 root->lock=h;wf_close(w);lua_pushboolean(L,1);return 1;}
static int remove_file(lua_State *L){WF *root=root_arg(L),*w;size_t n;const char *p=path_arg(L,2,&n);FILE_DISPOSITION_INFO remove={TRUE};
 if(!wf_file(L,root,p,n,DELETE,0,&w)){DWORD e=GetLastError();wf_close(w);if(e==ERROR_FILE_NOT_FOUND||e==ERROR_PATH_NOT_FOUND){lua_pushboolean(L,1);return 1;}SetLastError(e);return wf_fail(L,"remover arquivo");}
 if(!SetFileInformationByHandle(w->h[w->n-1],FileDispositionInfo,&remove,sizeof(remove))){wf_close(w);return wf_fail(L,"remover arquivo");}wf_close(w);lua_pushboolean(L,1);return 1;}
static int list_directory(lua_State *L){WF *root=root_arg(L),*w;size_t n;const char *p=luaL_optlstring(L,2,"",&n);wchar_t rel[WF_MAX];WIN32_FIND_DATAW item;WF_ENUM *search;int more=0,count=0,out;
 w=wf_new(L);if(!wf_copy(w,root))goto fail;
 if(n && (!wf_relative(p,n,rel)||!wf_walk(w,rel,0)))goto fail;
 search=lua_newuserdata(L,sizeof(*search));memset(search,0,sizeof(*search));
#ifdef SANTAFE_DADOS_EXPERIMENTAL
 lua_createlist(L,0);
#else
 lua_newtable(L);
#endif
 out=lua_gettop(L);
 while((more=wf_next(w->h[w->n-1],search,&item))>0){char name[1024];const char *type;
  if(!wcscmp(item.cFileName,L".")||!wcscmp(item.cFileName,L".."))continue;
  if(++count>8192 || !wf_utf8(item.cFileName,name,sizeof(name))){SetLastError(ERROR_BUFFER_OVERFLOW);goto fail;}
  type=(item.dwFileAttributes&FILE_ATTRIBUTE_REPARSE_POINT)?"especial":(item.dwFileAttributes&FILE_ATTRIBUTE_DIRECTORY)?"diretorio":"arquivo";
  lua_newtable(L);lua_pushstring(L,name);lua_setfield(L,-2,"nome");lua_pushstring(L,type);lua_setfield(L,-2,"tipo");lua_rawseti(L,out,count);
 }
 wf_close(w);if(more<0)return wf_fail(L,"listar diretorio");
 return 1;
fail:wf_close(w);return wf_fail(L,"listar diretorio");}
static int digest(lua_State *L) {
    size_t n; const char *s=luaL_checklstring(L,1,&n); Memory *m=memory(L);
    m->p=g_compute_checksum_for_data(G_CHECKSUM_SHA256,(const guchar*)s,n);
    lua_pushstring(L,m->p); g_free(m->p); m->p=NULL; return 1;
}
static int base64(lua_State *L) {
    size_t n; const char *s=luaL_checklstring(L,1,&n); Memory *m=memory(L);
    luaL_argcheck(L,n<=MAX_BYTES,1,"conteudo excessivo");
    m->p=g_base64_encode((const guchar*)s,n); lua_pushstring(L,m->p); g_free(m->p); m->p=NULL; return 1;
}
static int unbase64(lua_State *L) {
    size_t n,i,pad=0; gsize out; const char *s=luaL_checklstring(L,1,&n); Memory *m;
    luaL_argcheck(L,n<=MAX_BYTES && n%4==0,1,"base64 invalido");
    if(n && s[n-1]=='=') pad++;
    if(n>1 && s[n-2]=='=') pad++;
    for(i=0;i<n-pad;i++) luaL_argcheck(L,(s[i]>='A'&&s[i]<='Z')||(s[i]>='a'&&s[i]<='z')||(s[i]>='0'&&s[i]<='9')||s[i]=='+'||s[i]=='/',1,"base64 invalido");
    m=memory(L); m->p=g_base64_decode(s,&out);
    /* Require canonical padding bits, not just alphabet. */
    { gchar *canonical=g_base64_encode(m->p,out); int same=strlen(canonical)==n && !memcmp(canonical,s,n); g_free(canonical); if(!same) return luaL_argerror(L,1,"base64 nao canonico"); }
    lua_pushlstring(L,m->p,out); g_free(m->p); m->p=NULL; return 1;
}
static int path_key(lua_State *L) {
    size_t n; const char *s=luaL_checklstring(L,1,&n); Memory *m=memory(L); gchar *normalized;
    luaL_argcheck(L,valid_path(s,n),1,"caminho inseguro");
    normalized=g_utf8_normalize(s,n,G_NORMALIZE_NFC); m->p=g_utf8_casefold(normalized,-1); g_free(normalized);
    lua_pushstring(L,m->p); g_free(m->p); m->p=NULL; return 1;
}
static int append_arg(wchar_t *out,size_t *used,const wchar_t *arg) {
    size_t i=0,slashes=0; if(*used)out[(*used)++]=L' ';out[(*used)++]=L'"';
    while(arg[i]){
        if(*used+8>=32760)return 0;
        if(arg[i]==L'\\'){slashes++;i++;continue;}
        if(*used+2*slashes+4>=32760)return 0;
        while(slashes){out[(*used)++]=L'\\';if(arg[i]==L'"')out[(*used)++]=L'\\';slashes--;}
        if(arg[i]==L'"')out[(*used)++]=L'\\';
        out[(*used)++]=arg[i++];
    }
    if(*used+2*slashes+2>=32760)return 0;
    while(slashes--){out[(*used)++]=L'\\';out[(*used)++]=L'\\';}out[(*used)++]=L'"';out[*used]=0;return 1;
}
static int absolute(const wchar_t *p){return ((p[0]>=L'A'&&p[0]<=L'Z')||(p[0]>=L'a'&&p[0]<=L'z'))&&p[1]==L':'&&(p[2]==L'/'||p[2]==L'\\');}
static int run(lua_State *L){
 WF *root=root_arg(L),*pins=NULL;lua_Integer seconds=luaL_optinteger(L,3,120),max=luaL_optinteger(L,4,1024*1024);size_t count,used=0,bytes=0;int i,code=0,started=0;DWORD error=ERROR_SUCCESS,available,n,exitcode=0;
 wchar_t command[32768],exe[WF_MAX],arg[WF_MAX],system[WF_MAX],compiler[WF_MAX],environment[32768];char *output;
 HANDLE rd=NULL,wr=NULL,in=NULL,job=NULL,inherit[2];STARTUPINFOEXW startup;PROCESS_INFORMATION process;SECURITY_ATTRIBUTES sa={sizeof(sa),NULL,TRUE};JOBOBJECT_EXTENDED_LIMIT_INFORMATION limits;SIZE_T attrs=0;ULONGLONG end;
 luaL_argcheck(L,lua_istable(L,2),2,"argumentos invalidos");count=lua_rawlen(L,2);
 luaL_argcheck(L,count>0&&count<=256,2,"limite de argumentos");luaL_argcheck(L,seconds>=1&&seconds<=180,3,"prazo invalido");luaL_argcheck(L,max>0&&max<=MAX_BYTES,4,"limite de saida invalido");
 for(i=1;i<=(int)count;i++){size_t size;const char *s;lua_rawgeti(L,2,i);s=luaL_checklstring(L,-1,&size);if(!size)arg[0]=0;else if(!wf_wide(s,size,arg,WF_MAX))return luaL_argerror(L,2,"argumento UTF8 invalido ou excessivo");
  if(!append_arg(command,&used,arg))return luaL_argerror(L,2,"comando excessivo");
  if(i==1)wcscpy(exe,arg);
  lua_pop(L,1);}
 luaL_argcheck(L,absolute(exe)&&wcslen(exe)>4&&!_wcsicmp(exe+wcslen(exe)-4,L".exe"),2,"executavel absoluto .exe exigido");
 wcscpy(compiler,exe);{wchar_t *slash=wcsrchr(compiler,L'\\'),*other=wcsrchr(compiler,L'/');if(other&&(!slash||other>slash))slash=other;*slash=0;}
 if(!GetWindowsDirectoryW(system,WF_MAX))return wf_fail(L,"diretorio Windows");
 {int len=swprintf(environment,32768,L"PATH=%ls;%ls\\System32%cSystemRoot=%ls%cTEMP=%ls%cTMP=%ls%c",compiler,system,0,system,0,root->path,0,root->path,0);if(len<=0||len>=32767)return luaL_error(L,"ambiente excessivo");environment[len]=0;}
 output=lua_newuserdata(L,(size_t)max+1);memset(&startup,0,sizeof(startup));memset(&process,0,sizeof(process));memset(&limits,0,sizeof(limits));startup.StartupInfo.cb=sizeof(startup);
 pins=wf_new(L);if(!wf_strict(pins,root))goto fail;
 if(!CreatePipe(&rd,&wr,&sa,0)||!SetHandleInformation(rd,HANDLE_FLAG_INHERIT,0))goto fail;
 in=CreateFileW(L"NUL",GENERIC_READ,FILE_SHARE_READ|FILE_SHARE_WRITE,&sa,OPEN_EXISTING,0,NULL);if(in==INVALID_HANDLE_VALUE){in=NULL;goto fail;}
 job=CreateJobObjectW(NULL,NULL);if(!job)goto fail;limits.BasicLimitInformation.LimitFlags=JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE|JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION;
 if(!SetInformationJobObject(job,JobObjectExtendedLimitInformation,&limits,sizeof(limits)))goto fail;
 InitializeProcThreadAttributeList(NULL,2,0,&attrs);startup.lpAttributeList=malloc(attrs);if(!startup.lpAttributeList){SetLastError(ERROR_NOT_ENOUGH_MEMORY);goto fail;}
 if(!InitializeProcThreadAttributeList(startup.lpAttributeList,2,0,&attrs)) {free(startup.lpAttributeList);startup.lpAttributeList=NULL;goto fail;}
 inherit[0]=wr;inherit[1]=in;
 if(!UpdateProcThreadAttribute(startup.lpAttributeList,0,PROC_THREAD_ATTRIBUTE_HANDLE_LIST,inherit,sizeof(inherit),NULL,NULL)||
    !UpdateProcThreadAttribute(startup.lpAttributeList,0,PROC_THREAD_ATTRIBUTE_JOB_LIST,&job,sizeof(job),NULL,NULL))goto fail;
 startup.StartupInfo.dwFlags=STARTF_USESTDHANDLES;startup.StartupInfo.hStdOutput=wr;startup.StartupInfo.hStdError=wr;startup.StartupInfo.hStdInput=in;
 if(!CreateProcessW(exe,command,NULL,NULL,TRUE,CREATE_UNICODE_ENVIRONMENT|EXTENDED_STARTUPINFO_PRESENT|CREATE_NO_WINDOW,environment,root->path,&startup.StartupInfo,&process))goto fail;
 started=1;CloseHandle(wr);wr=NULL;CloseHandle(in);in=NULL;end=GetTickCount64()+1000*(ULONGLONG)seconds;
 for(;;){
  while(PeekNamedPipe(rd,NULL,0,NULL,&available,NULL)&&available){char b[4096];if(!ReadFile(rd,b,available>sizeof(b)?sizeof(b):available,&n,NULL)||!n)break;
   if(bytes+n>(size_t)max){code=125;goto stop;}memcpy(output+bytes,b,n);bytes+=n;}
  if(WaitForSingleObject(process.hProcess,0)==WAIT_OBJECT_0){if(!GetExitCodeProcess(process.hProcess,&exitcode))goto fail;code=(int)exitcode;break;}
  if(GetTickCount64()>=end){code=124;goto stop;}Sleep(5);
 }
stop:
 /* Closing this job kills any remaining descendant, including after a normal
  * parent exit. No PID-based termination and no recycled process identifiers. */
 if(job){CloseHandle(job);job=NULL;}
 WaitForSingleObject(process.hProcess,5000);
 while(PeekNamedPipe(rd,NULL,0,NULL,&available,NULL)&&available){char b[4096];if(!ReadFile(rd,b,available>sizeof(b)?sizeof(b):available,&n,NULL)||!n)break;if(bytes+n>(size_t)max){code=125;break;}memcpy(output+bytes,b,n);bytes+=n;}
 goto cleanup;
fail:error=GetLastError();if(!error)error=ERROR_GEN_FAILURE;
cleanup:
 if(pins)wf_close(pins);
 if(job)CloseHandle(job);
 if(started){CloseHandle(process.hThread);CloseHandle(process.hProcess);}if(rd)CloseHandle(rd);if(wr)CloseHandle(wr);if(in)CloseHandle(in);
 if(startup.lpAttributeList){DeleteProcThreadAttributeList(startup.lpAttributeList);free(startup.lpAttributeList);}
 if(error){SetLastError(error);return wf_fail(L,"executar processo confinado");}lua_pushinteger(L,code);lua_pushlstring(L,output,bytes);return 2;
}
static int cwd(lua_State *L){wchar_t p[WF_MAX];char out[WF_MAX*3];size_t i;if(!GetCurrentDirectoryW(WF_MAX,p)||!wf_utf8(p,out,sizeof(out)))return wf_fail(L,"diretorio atual");for(i=0;out[i];i++)if(out[i]=='\\')out[i]='/';lua_pushstring(L,out);return 1;}
static int platform(lua_State *L){lua_newtable(L);lua_pushliteral(L,"Windows");lua_setfield(L,-2,"sistema");lua_pushliteral(L,"x86_64");lua_setfield(L,-2,"maquina");lua_pushinteger(L,LUA_VERSION_NUM);lua_setfield(L,-2,"abi");
#ifdef SANTAFE_DADOS_EXPERIMENTAL
lua_pushinteger(L,LUAL_NUMSIZES);lua_setfield(L,-2,"abiDados");
#endif
lua_pushinteger(L,sizeof(void*)*8);lua_setfield(L,-2,"ponteiros");return 1;}
static int nonce(lua_State *L){unsigned char b[16];char s[33];int i;if(!random_bytes(b,16))return wf_fail(L,"aleatoriedade");for(i=0;i<16;i++)sprintf(s+2*i,"%02x",b[i]);lua_pushlstring(L,s,32);return 1;}
static int tool(lua_State *L){const char *name=luaL_checkstring(L,1);wchar_t p[WF_MAX];char out[WF_MAX*3];DWORD n;
 if(!strcmp(name,"curl")){n=GetSystemDirectoryW(p,WF_MAX);if(!n||n+10>=WF_MAX)return wf_fail(L,"curl do sistema");wcscat(p,L"\\curl.exe");}
 else if(!strcmp(name,"cc")){n=GetEnvironmentVariableW(L"SANTAFE_CC",p,WF_MAX);if(!n||n>=WF_MAX){SetLastError(ERROR_NOT_SUPPORTED);return wf_fail(L,"configure SANTAFE_CC com compilador absoluto confiavel");}}
 else return luaL_error(L,"ferramenta desconhecida");
 if(!absolute(p)||!wf_utf8(p,out,sizeof(out)))return wf_fail(L,"ferramenta absoluta exigida");
 lua_pushstring(L,out);return 1;
}
__declspec(dllexport) int luaopen_pacotes_nativo(lua_State *L){
 const luaL_Reg methods[]={{"leia",read_file},{"grave",write_file},{"diretorio",mkdirs},{"subraiz",subroot},{"existe",exists},{"liste",list_directory},{"trave",lock_root},{"execute",run},{"removaArquivo",remove_file},{"feche",wf_gc},{NULL,NULL}};
 const luaL_Reg api[]={{"raiz",open_root},{"sha256",digest},{"base64",base64},{"decodBase64",unbase64},{"chaveCaminho",path_key},{"diretorioAtual",cwd},{"plataforma",platform},{"nonce",nonce},{"ferramenta",tool},{NULL,NULL}};
 luaL_checkversion(L);wf_register(L);luaL_getmetatable(L,WF_MT);lua_newtable(L);luaL_setfuncs(L,methods,0);lua_setfield(L,-2,LUA_MM_INDICE);lua_pop(L,1);
 if(luaL_newmetatable(L,MEMORY)){lua_pushcfunction(L,gc_memory);lua_setfield(L,-2,LUA_MM_FINALIZE);}lua_pop(L,1);
 luaL_newlib(L,api);return 1;
}
