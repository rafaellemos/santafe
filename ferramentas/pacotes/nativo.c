/* Private package-manager I/O. POSIX, no shell, pinned directory capabilities.
 * Every untrusted path component is opened with O_NOFOLLOW. */
#define _POSIX_C_SOURCE 200809L
#ifdef __APPLE__
#define _DARWIN_C_SOURCE 1
#endif
#include <errno.h>
#include <dirent.h>
#include <fcntl.h>
#include <glib.h>
#include <poll.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/file.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <sys/utsname.h>
#include <time.h>
#include <unistd.h>
#include "lua.h"
#include "lauxlib.h"

#define HANDLE "Pacotes.raiz"
#define MEMORY "Pacotes.memoria"
#define DIRECTORY "Pacotes.diretorio"
#define MAX_BYTES (64 * 1024 * 1024)
typedef struct { int fd, lock; } Handle;
typedef struct { void *p; } Memory;
typedef struct { DIR *p; } Directory;
static int gc_handle(lua_State *L) {
    Handle *h=lua_touserdata(L,1);
    if(h->fd>=0) { close(h->fd); h->fd=-1; }
    if(h->lock>=0) { close(h->lock); h->lock=-1; }
    return 0;
}
static int gc_memory(lua_State *L) { Memory *m=lua_touserdata(L,1); g_free(m->p); m->p=NULL; return 0; }
static int gc_directory(lua_State *L) { Directory *d=lua_touserdata(L,1); if(d->p) closedir(d->p); d->p=NULL; return 0; }
static Handle *handle(lua_State *L) {
    Handle *h=lua_newuserdata(L,sizeof(*h)); h->fd=h->lock=-1;
    luaL_getmetatable(L,HANDLE); lua_setmetatable(L,-2); return h;
}
static Memory *memory(lua_State *L) {
    Memory *m=lua_newuserdata(L,sizeof(*m)); m->p=NULL;
    luaL_getmetatable(L,MEMORY); lua_setmetatable(L,-2); return m;
}
static int failure(lua_State *L,const char *msg) {
    int e=errno; lua_pushnil(L); lua_pushfstring(L,"%s: %s",msg,strerror(e)); lua_pushinteger(L,e); return 3;
}
static int valid_path(const char *s,size_t n) {
    size_t start=0,i;
    if(!n || n>2048 || s[0]=='/' || s[n-1]=='/' || strlen(s)!=n || !g_utf8_validate(s,n,NULL)) return 0;
    for(i=0;i<=n;i++) {
        if(i<n && ((unsigned char)s[i]<32 || s[i]==127 || s[i]=='\\' || s[i]==':' || s[i]==';' || s[i]=='?')) return 0;
        if(i==n || s[i]=='/') {
            size_t k=i-start;
            if(!k || k>255 || (k==1 && s[start]=='.') || (k==2 && s[start]=='.' && s[start+1]=='.')) return 0;
            start=i+1;
        }
    }
    return 1;
}
static const char *path_arg(lua_State *L,int index) {
    size_t n; const char *s=luaL_checklstring(L,index,&n);
    luaL_argcheck(L,valid_path(s,n),index,"caminho relativo inseguro"); return s;
}
/* Returns a pinned parent; last component copied to leaf. No Lua allocations. */
static int parent_fd(int root,const char *path,char leaf[256],int create) {
    int fd=dup(root); const char *p=path,*slash;
    if(fd<0) return -1;
    fcntl(fd,F_SETFD,FD_CLOEXEC);
    while((slash=strchr(p,'/'))) {
        int next; size_t n=(size_t)(slash-p);
        memcpy(leaf,p,n); leaf[n]=0;
        if(create && mkdirat(fd,leaf,0700) && errno!=EEXIST) { close(fd); return -1; }
        next=openat(fd,leaf,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
        close(fd); if(next<0) return -1;
        fd=next; p=slash+1;
    }
    strcpy(leaf,p); return fd;
}
static Handle *root_arg(lua_State *L) {
    Handle *h=luaL_checkudata(L,1,HANDLE);
    luaL_argcheck(L,h->fd>=0,1,"raiz fechada"); return h;
}
static int open_root(lua_State *L) {
    size_t n; const char *path=luaL_checklstring(L,1,&n); Handle *h;
    luaL_argcheck(L,n && strlen(path)==n,1,"raiz invalida");
    h=handle(L); h->fd=open(path,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    if(h->fd<0) return failure(L,"abrir raiz");
    return 1;
}
static int open_relative(lua_State *L) {
    Handle *root=root_arg(L),*h; const char *p=path_arg(L,2); char leaf[256]; int fd;
    h=handle(L); fd=parent_fd(root->fd,p,leaf,0);
    if(fd<0) return failure(L,"abrir subdiretorio");
    h->fd=openat(fd,leaf,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC); close(fd);
    if(h->fd<0) return failure(L,"abrir subdiretorio");
    return 1;
}
static int make_directory(lua_State *L) {
    Handle *root=root_arg(L); const char *p=path_arg(L,2); char leaf[256]; int fd,next;
    fd=parent_fd(root->fd,p,leaf,1); if(fd<0) return failure(L,"criar diretorios");
    if(mkdirat(fd,leaf,0700) && errno!=EEXIST) { close(fd); return failure(L,"criar diretorio"); }
    next=openat(fd,leaf,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC); close(fd);
    if(next<0) return failure(L,"diretorio inseguro");
    close(next); lua_pushboolean(L,1); return 1;
}
static int read_file(lua_State *L) {
    Handle *root=root_arg(L),*h; const char *p=path_arg(L,2); char leaf[256]; int parent;
    lua_Integer limit=luaL_optinteger(L,3,MAX_BYTES); struct stat st; size_t used=0,size; char *buffer;
    luaL_argcheck(L,limit>0 && limit<=MAX_BYTES,3,"limite invalido");
    h=handle(L); parent=parent_fd(root->fd,p,leaf,0);
    if(parent<0) return failure(L,"ler arquivo");
    h->fd=openat(parent,leaf,O_RDONLY|O_NOFOLLOW|O_CLOEXEC|O_NONBLOCK); close(parent);
    if(h->fd<0) return failure(L,"ler arquivo");
    if(fstat(h->fd,&st) || !S_ISREG(st.st_mode) || st.st_size<0 || st.st_size>limit) {
        close(h->fd); h->fd=-1; errno=EINVAL; return failure(L,"arquivo nao regular ou excessivo");
    }
    size=(size_t)st.st_size; buffer=lua_newuserdata(L,size+1);
    while(used<size+1) {
        ssize_t n=read(h->fd,buffer+used,size+1-used);
        if(n<0 && errno==EINTR) continue;
        if(n<0) { close(h->fd); h->fd=-1; return failure(L,"leitura"); }
        if(!n) break;
        used+=(size_t)n;
    }
    close(h->fd); h->fd=-1;
    if(used!=size) { errno=EAGAIN; return failure(L,"arquivo alterado durante leitura"); }
    lua_pushlstring(L,buffer,used); return 1;
}
static int exists(lua_State *L) {
    Handle *root=root_arg(L); const char *p=path_arg(L,2); char leaf[256]; int fd,rc; struct stat st;
    fd=parent_fd(root->fd,p,leaf,0);
    if(fd<0) { if(errno==ENOENT) { lua_pushboolean(L,0); return 1; } return failure(L,"consultar caminho"); }
    rc=fstatat(fd,leaf,&st,AT_SYMLINK_NOFOLLOW); close(fd);
    if(rc) { if(errno==ENOENT) { lua_pushboolean(L,0); return 1; } return failure(L,"consultar caminho"); }
    if(!S_ISREG(st.st_mode) && !S_ISDIR(st.st_mode)) { errno=EINVAL; return failure(L,"caminho especial nao permitido"); }
    lua_pushstring(L,S_ISREG(st.st_mode)?"arquivo":"diretorio"); return 1;
}
static int write_file(lua_State *L) {
    Handle *root=root_arg(L); const char *p=path_arg(L,2); size_t n,used=0;
    const char *bytes=luaL_checklstring(L,3,&n); int replace=lua_toboolean(L,4);
    char leaf[256],temporary[96]; int parent,fd,rc; unsigned counter; static unsigned serial;
    luaL_argcheck(L,n<=MAX_BYTES,3,"arquivo excessivo");
    parent=parent_fd(root->fd,p,leaf,0); if(parent<0) return failure(L,"gravar arquivo");
    for(counter=0;counter<100;counter++) {
        snprintf(temporary,sizeof(temporary),".escrita-%ld-%u",(long)getpid(),++serial);
        fd=openat(parent,temporary,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0600);
        if(fd>=0 || errno!=EEXIST) break;
    }
    if(fd<0) { close(parent); return failure(L,"criar arquivo temporario"); }
    while(used<n) {
        ssize_t k=write(fd,bytes+used,n-used);
        if(k<0 && errno==EINTR) continue;
        if(k<=0) goto failed;
        used+=(size_t)k;
    }
    if(fsync(fd)) goto failed;
    if(close(fd)) { fd=-1; goto failed; } fd=-1;
    if(replace) rc=renameat(parent,temporary,parent,leaf);
    else { rc=linkat(parent,temporary,parent,leaf,0); if(!rc) unlinkat(parent,temporary,0); }
    if(rc || fsync(parent)) goto failed;
    close(parent); lua_pushboolean(L,1); return 1;
failed:
    { int saved=errno; if(fd>=0) close(fd); unlinkat(parent,temporary,0); close(parent); errno=saved; }
    return failure(L,"gravar arquivo atomico");
}
static int lock_root(lua_State *L) {
    Handle *h=root_arg(L); int parent,fd; char leaf[256]; struct stat st;
    luaL_argcheck(L,h->lock<0,1,"raiz ja travada");
    parent=parent_fd(h->fd,".santafe/trava",leaf,1);
    if(parent<0) return failure(L,"diretorio da trava");
    fd=openat(parent,leaf,O_RDWR|O_CREAT|O_NOFOLLOW|O_CLOEXEC|O_NONBLOCK,0600); close(parent);
    if(fd<0) return failure(L,"abrir trava");
    if(fstat(fd,&st) || !S_ISREG(st.st_mode) || st.st_nlink!=1 || st.st_uid!=getuid()) { close(fd); errno=EPERM; return failure(L,"trava insegura"); }
    if(flock(fd,LOCK_EX|LOCK_NB)) { close(fd); return failure(L,"outra instalacao esta em andamento"); }
    h->lock=fd; lua_pushboolean(L,1); return 1;
}
static int remove_file(lua_State *L) {
    Handle *root=root_arg(L); const char *p=path_arg(L,2); char leaf[256]; int fd,rc; struct stat st;
    fd=parent_fd(root->fd,p,leaf,0); if(fd<0) return failure(L,"remover arquivo");
    rc=fstatat(fd,leaf,&st,AT_SYMLINK_NOFOLLOW);
    if(rc && errno==ENOENT) { close(fd); lua_pushboolean(L,1); return 1; }
    if(rc || !S_ISREG(st.st_mode)) { close(fd); errno=EINVAL; return failure(L,"remocao exige arquivo regular"); }
    rc=unlinkat(fd,leaf,0); if(!rc) rc=fsync(fd); close(fd);
    if(rc) return failure(L,"remover arquivo");
    lua_pushboolean(L,1); return 1;
}
static int list_directory(lua_State *L) {
    Handle *root=root_arg(L); const char *p=luaL_optstring(L,2,""); char leaf[256]; int fd,parent,output,count=0; Directory *d; struct dirent *entry;
    if(*p) path_arg(L,2);
    d=lua_newuserdata(L,sizeof(*d)); d->p=NULL; luaL_getmetatable(L,DIRECTORY); lua_setmetatable(L,-2);
    if(!*p) fd=dup(root->fd);
    else { parent=parent_fd(root->fd,p,leaf,0); if(parent<0) return failure(L,"listar"); fd=openat(parent,leaf,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC); close(parent); }
    if(fd<0) return failure(L,"listar");
    d->p=fdopendir(fd); if(!d->p) { close(fd); return failure(L,"listar"); }
#ifdef SANTAFE_DADOS_V3
    lua_createlist(L,0);
#else
    lua_newtable(L);
#endif
    output=lua_gettop(L);
    while(1) {
        struct stat st; errno=0; entry=readdir(d->p);
        if(!entry) { int e=errno; closedir(d->p); d->p=NULL; if(e) { errno=e; return failure(L,"listar"); } return 1; }
        if(!strcmp(entry->d_name,".") || !strcmp(entry->d_name,"..")) continue;
        if(++count>8192 || fstatat(fd,entry->d_name,&st,AT_SYMLINK_NOFOLLOW)) { closedir(d->p); d->p=NULL; errno=E2BIG; return failure(L,"diretorio excessivo ou alterado"); }
        lua_newtable(L); lua_pushstring(L,entry->d_name); lua_setfield(L,-2,"nome");
        lua_pushstring(L,S_ISREG(st.st_mode)?"arquivo":S_ISDIR(st.st_mode)?"diretorio":"especial"); lua_setfield(L,-2,"tipo");
        lua_rawseti(L,output,count);
    }
}
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
static double monotonic(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC,&t); return (double)t.tv_sec+(double)t.tv_nsec/1e9; }
static int run(lua_State *L) {
    Handle *root=root_arg(L); char *args[258]; int count,i,pipes[2],status=0,done=0,overflow=0,timeout=0; pid_t pid;
    size_t total=0,used=0; char *output; double end; lua_Integer seconds=luaL_optinteger(L,3,120), maximum=luaL_optinteger(L,4,1024*1024);
    luaL_checktype(L,2,LUA_TTABLE);
    luaL_argcheck(L,lua_rawlen(L,2)>0 && lua_rawlen(L,2)<=256,2,"argumentos invalidos"); count=(int)lua_rawlen(L,2);
    luaL_argcheck(L,seconds>=1 && seconds<=180,3,"prazo invalido");
    luaL_argcheck(L,maximum>=1 && maximum<=MAX_BYTES,4,"limite de saida invalido");
    for(i=0;i<count;i++) { size_t n; lua_rawgeti(L,2,i+1); luaL_checktype(L,-1,LUA_TSTRING); args[i]=(char*)luaL_checklstring(L,-1,&n); luaL_argcheck(L,n==strlen(args[i]),2,"NUL no argumento"); total+=n; lua_pop(L,1); }
    args[count]=NULL; luaL_argcheck(L,args[0][0]=='/' && total<=128*1024,2,"executavel absoluto e argumentos limitados exigidos");
    output=lua_newuserdata(L,(size_t)maximum+1);
    if(pipe(pipes)) return failure(L,"criar canal");
    fcntl(pipes[0],F_SETFD,FD_CLOEXEC); fcntl(pipes[1],F_SETFD,FD_CLOEXEC);
    pid=fork();
    if(pid<0) { close(pipes[0]); close(pipes[1]); return failure(L,"iniciar processo"); }
    if(pid==0) {
        struct rlimit core={0,0}; char *environment[]={"PATH=/usr/bin:/bin:/usr/local/bin","LC_ALL=C","LANG=C","TMPDIR=.",NULL}; int nullfd;
        setpgid(0,0); setrlimit(RLIMIT_CORE,&core); close(pipes[0]);
        if(fchdir(root->fd)) _exit(126);
        nullfd=open("/dev/null",O_RDONLY); if(nullfd>=0) { dup2(nullfd,STDIN_FILENO); close(nullfd); }
        dup2(pipes[1],STDOUT_FILENO); dup2(pipes[1],STDERR_FILENO); close(pipes[1]);
        execve(args[0],args,environment); _exit(127);
    }
    setpgid(pid,pid); close(pipes[1]); fcntl(pipes[0],F_SETFL,O_NONBLOCK); end=monotonic()+seconds;
    while(!done) {
        char buffer[4096]; ssize_t n; struct pollfd p={pipes[0],POLLIN,0}; poll(&p,1,20);
        while((n=read(pipes[0],buffer,sizeof(buffer)))>0) {
            if(used+(size_t)n>(size_t)maximum) { overflow=1; break; }
            memcpy(output+used,buffer,n); used+=(size_t)n;
        }
        if(monotonic()>end) timeout=1;
        if(overflow || timeout) { kill(-pid,SIGKILL); kill(pid,SIGKILL); }
        { pid_t rc=waitpid(pid,&status,WNOHANG); if(rc==pid || (rc<0 && errno!=EINTR)) done=1; }
    }
    /* Drain bytes written between the last read and waitpid. Descendants do
     * not delay this read; no signal is sent to a potentially recycled PID. */
    { ssize_t n; char buffer[4096];
      while((n=read(pipes[0],buffer,sizeof(buffer)))>0) {
        if(used+(size_t)n>(size_t)maximum) { overflow=1; break; }
        memcpy(output+used,buffer,n); used+=(size_t)n;
      }
    }
    close(pipes[0]);
    lua_pushinteger(L,timeout?124:overflow?125:WIFEXITED(status)?WEXITSTATUS(status):128+WTERMSIG(status));
    lua_pushlstring(L,output,used); return 2;
}
static int cwd(lua_State *L) {
    char buffer[8192]; if(!getcwd(buffer,sizeof(buffer))) return failure(L,"diretorio atual"); lua_pushstring(L,buffer); return 1;
}
static int platform(lua_State *L) {
    struct utsname u; if(uname(&u)) return failure(L,"plataforma");
    lua_newtable(L); lua_pushstring(L,u.sysname); lua_setfield(L,-2,"sistema");
    lua_pushstring(L,u.machine); lua_setfield(L,-2,"maquina");
    lua_pushinteger(L,LUA_VERSION_NUM); lua_setfield(L,-2,"abi");
#ifdef SANTAFE_DADOS_V3
    lua_pushinteger(L,LUAL_NUMSIZES); lua_setfield(L,-2,"abiDados");
    lua_pushstring(L,SANTAFE_ABI_ID); lua_setfield(L,-2,"iba");
    lua_pushinteger(L,SANTAFE_BYTECODE_VERSION); lua_setfield(L,-2,"bytecode");
#endif
    lua_pushinteger(L,sizeof(void*)*8); lua_setfield(L,-2,"ponteiros"); return 1;
}
static int nonce(lua_State *L) {
    unsigned char bytes[16]; char hex[33]; size_t used=0,i; int fd=open("/dev/urandom",O_RDONLY|O_CLOEXEC);
    if(fd<0) return failure(L,"aleatoriedade");
    while(used<sizeof(bytes)) { ssize_t n=read(fd,bytes+used,sizeof(bytes)-used); if(n<0 && errno==EINTR) continue; if(n<=0) { close(fd); return failure(L,"aleatoriedade"); } used+=(size_t)n; }
    close(fd); for(i=0;i<16;i++) snprintf(hex+2*i,3,"%02x",bytes[i]); lua_pushlstring(L,hex,32); return 1;
}
static const luaL_Reg methods[]={
    {"leia",read_file},{"grave",write_file},{"diretorio",make_directory},{"subraiz",open_relative},
    {"existe",exists},{"liste",list_directory},{"trave",lock_root},{"execute",run},{"removaArquivo",remove_file},{"feche",gc_handle},{NULL,NULL}};
LUAMOD_API int luaopen_pacotes_nativo(lua_State *L) {
    luaL_checkversion(L);
    luaL_newmetatable(L,HANDLE); lua_pushcfunction(L,gc_handle); lua_setfield(L,-2,LUA_MM_FINALIZE); lua_newtable(L); luaL_setfuncs(L,methods,0); lua_setfield(L,-2,LUA_MM_INDICE); lua_pop(L,1);
    luaL_newmetatable(L,MEMORY); lua_pushcfunction(L,gc_memory); lua_setfield(L,-2,LUA_MM_FINALIZE); lua_pop(L,1);
    luaL_newmetatable(L,DIRECTORY); lua_pushcfunction(L,gc_directory); lua_setfield(L,-2,LUA_MM_FINALIZE); lua_pop(L,1);
    { const luaL_Reg api[]={{"raiz",open_root},{"sha256",digest},{"base64",base64},{"decodBase64",unbase64},{"chaveCaminho",path_key},{"diretorioAtual",cwd},{"plataforma",platform},{"nonce",nonce},{NULL,NULL}}; luaL_newlib(L,api); }
    return 1;
}

#if defined(SANTAFE_DADOS_V3)
SANTAFE_MODULE_ABI;
#endif
