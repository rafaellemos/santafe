/* Private POSIX support for SLS. No shell, network or workspace execution.
 * Open each relative component using a directory descriptor and O_NOFOLLOW;
 * a regular bounded file is the only accepted result. */
#define _POSIX_C_SOURCE 200809L
#if defined(__APPLE__)
#define _DARWIN_C_SOURCE 1
#endif
#include <errno.h>
#include <dirent.h>
#include <fcntl.h>
#include <poll.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
#include "lua.h"
#include "lauxlib.h"
#if defined(SANTAFE_SLS_EMBUTIDO)
#if defined(__APPLE__)
#include <CommonCrypto/CommonDigest.h>
#define SLS_SHA256_SIZE CC_SHA256_DIGEST_LENGTH
#else
#include <openssl/sha.h>
#define SLS_SHA256_SIZE SHA256_DIGEST_LENGTH
#endif
static int hash_source(lua_State *L) {
    size_t size, i;
    const char *source = luaL_checklstring(L, 1, &size);
    unsigned char digest[SLS_SHA256_SIZE];
    char hex[SLS_SHA256_SIZE * 2 + 1];
    static const char digits[] = "0123456789abcdef";
    luaL_argcheck(L, size <= 16 * 1024 * 1024, 1, "fonte excessiva");
#if defined(__APPLE__)
    CC_SHA256(source, (CC_LONG)size, digest);
#else
    if (!SHA256((const unsigned char *)source, size, digest))
        return luaL_error(L, "SHA-256 indisponível");
#endif
    for (i=0; i<sizeof(digest); i++) {
        hex[2*i]=digits[digest[i]>>4]; hex[2*i+1]=digits[digest[i]&15];
    }
    lua_pushlstring(L,hex,2*sizeof(digest)); return 1;
}
#endif

typedef struct { int fd; } Handle;
typedef struct { DIR *directory; } Directory;
static int close_handle(lua_State *L) {
    Handle *h = (Handle *)lua_touserdata(L, 1);
    if (h->fd >= 0) { close(h->fd); h->fd = -1; }
    return 0;
}
static int failure(lua_State *L, Handle *h, const char *message) {
    if (h->fd >= 0) { close(h->fd); h->fd = -1; }
    lua_pushnil(L); lua_pushstring(L, message); return 2;
}
static Handle *new_handle(lua_State *L) {
    Handle *h = (Handle *)lua_newuserdata(L, sizeof(*h)); h->fd = -1;
    luaL_getmetatable(L, "SLS.descritor"); lua_setmetatable(L, -2);
    return h;
}
static int open_root(lua_State *L) {
    size_t size;
    const char *path = luaL_checklstring(L, 1, &size);
    Handle *h;
    luaL_argcheck(L, size && path[0] == '/' && strlen(path) == size, 1, "raiz absoluta invalida");
    h = new_handle(L);
    h->fd = open(path, O_RDONLY | O_DIRECTORY | O_CLOEXEC);
    if (h->fd < 0) return failure(L, h, "raiz inacessivel");
    return 1;
}
static int read_source(lua_State *L) {
    size_t np;
    Handle *root = (Handle *)luaL_checkudata(L, 1, "SLS.descritor");
    const char *path = luaL_checklstring(L, 2, &np);
    lua_Integer limit = luaL_optinteger(L, 3, 4 * 1024 * 1024);
    struct stat st;
    size_t pos = 0, used = 0, size;
    char component[4096], *buffer;
    Handle *h;
    luaL_argcheck(L, np && path[0] != '/' && strlen(path) == np, 2, "caminho relativo invalido");
    luaL_argcheck(L, limit > 0 && limit <= 16 * 1024 * 1024, 3, "limite invalido");
    h = new_handle(L);
    /* Pinned at initialize, not reopened by pathname on each request. */
    h->fd = root->fd >= 0 ? dup(root->fd) : -1;
    if (h->fd < 0) return failure(L, h, "raiz inacessivel");
    while (pos < np) {
        size_t end = pos;
        int nextfd, flags;
        while (end < np && path[end] != '/') end++;
        size = end - pos;
        if (!size || size >= sizeof(component) || (size == 1 && path[pos] == '.') ||
            (size == 2 && path[pos] == '.' && path[pos+1] == '.'))
            return failure(L, h, "componente inseguro");
        memcpy(component, path + pos, size); component[size] = 0;
        flags = O_RDONLY | O_NOFOLLOW | O_CLOEXEC | O_NONBLOCK;
        if (end < np) flags |= O_DIRECTORY;
        nextfd = openat(h->fd, component, flags);
        if (nextfd < 0) return failure(L, h, "fonte ausente ou caminho nao permitido");
        close(h->fd); h->fd = nextfd;
        pos = end + 1;
    }
    if (path[np-1] == '/' || fstat(h->fd, &st) || !S_ISREG(st.st_mode) ||
        st.st_size < 0 || st.st_size > limit)
        return failure(L, h, "fonte nao regular ou excessiva");
    size = (size_t)st.st_size;
    /* GC owns both descriptor and buffer even if Lua allocation throws. */
    buffer = (char *)lua_newuserdata(L, size + 1);
    while (used < size + 1) {
        ssize_t n = read(h->fd, buffer + used, size + 1 - used);
        if (n < 0 && errno == EINTR) continue;
        if (n < 0) return failure(L, h, "leitura falhou");
        if (!n) break;
        used += (size_t)n;
    }
    if (used != size) return failure(L, h, "fonte mudou durante leitura");
    close(h->fd); h->fd = -1;
    lua_pushlstring(L, buffer, used); return 1;
}

static int close_directory(lua_State *L) {
    Directory *d = (Directory *)lua_touserdata(L, 1);
    if (d->directory) { closedir(d->directory); d->directory = NULL; }
    return 0;
}
typedef struct { int files, entries, directories; const char *problem; } Scan;
static int ignored_directory(const char *name) {
    return name[0] == '.' || !strcmp(name, "node_modules") || !strcmp(name, "dist") ||
           !strcmp(name, "build") || !strcmp(name, "construcao");
}
/* Only bounded regular source files, no links or special files. Directory
 * ownership is GC-visible before recursion/allocations so OOM cannot leak FDs. */
static void scan_directory(lua_State *L, int parent, const char *name,
                           const char *prefix, int output, Scan *scan, int depth) {
    Directory *owner;
    struct dirent *entry;
    int fd, stack = lua_gettop(L);
    luaL_checkstack(L, 8, "profundidade de indexacao");
    if (depth > 32 || ++scan->directories > 1024) {
        scan->problem = "limite de diretorios"; return;
    }
    owner = (Directory *)lua_newuserdata(L, sizeof(*owner)); owner->directory = NULL;
    luaL_getmetatable(L, "SLS.diretorio"); lua_setmetatable(L, -2);
    fd = openat(parent, name, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (fd < 0) { scan->problem = "diretorio inacessivel ou alterado"; lua_settop(L,stack); return; }
    owner->directory = fdopendir(fd);
    if (!owner->directory) { close(fd); scan->problem="diretorio ilegivel"; lua_settop(L,stack); return; }
    while (!scan->problem) {
        struct stat st;
        size_t n;
        char path[4096];
        errno = 0;
        entry = readdir(owner->directory);
        if (!entry) { if (errno) scan->problem = "leitura de diretorio falhou"; break; }
        if (++scan->entries > 20000) { scan->problem="limite de entradas"; break; }
        if (!strcmp(entry->d_name,".") || !strcmp(entry->d_name,"..")) continue;
        if (entry->d_name[0]=='.') continue;
        if (fstatat(fd,entry->d_name,&st,AT_SYMLINK_NOFOLLOW)) { scan->problem="entrada alterada"; break; }
        if (S_ISLNK(st.st_mode)) continue;
        n = strlen(prefix) + strlen(entry->d_name);
        if (n + 2 >= sizeof(path)) { scan->problem="caminho excessivo"; break; }
        strcpy(path,prefix); strcat(path,entry->d_name);
        if (S_ISDIR(st.st_mode) && !ignored_directory(entry->d_name)) {
            strcat(path,"/"); scan_directory(L,fd,entry->d_name,path,output,scan,depth+1);
        } else if (S_ISREG(st.st_mode) &&
                   ((n>=3 && !strcmp(path+n-3,".fe")) || (n>=4 && !strcmp(path+n-4,".f\xc3\xa9")))) {
            if (scan->files >= 512) { scan->problem="limite de 512 fontes"; break; }
            lua_pushstring(L,path); lua_rawseti(L,output,++scan->files);
        }
    }
    closedir(owner->directory); owner->directory=NULL;
    lua_settop(L,stack);
}
static int list_sources(lua_State *L) {
    Handle *root=(Handle *)luaL_checkudata(L,1,"SLS.descritor");
    Scan scan={0,0,0,NULL};
    lua_newtable(L);
    scan_directory(L,root->fd,".","",lua_gettop(L),&scan,0);
    if (scan.problem) lua_pushstring(L,scan.problem); else lua_pushnil(L);
    return 2;
}

static int input_ready(lua_State *L) {
    int ms = (int)luaL_optinteger(L, 1, 0);
    struct pollfd fd = { STDIN_FILENO, POLLIN, 0 };
    int result;
    luaL_argcheck(L, ms >= 0 && ms <= 1000, 1, "prazo invalido");
    do { result = poll(&fd, 1, ms); } while (result < 0 && errno == EINTR);
    if (result < 0) return luaL_error(L, "poll falhou");
    lua_pushboolean(L, result && (fd.revents & (POLLIN | POLLHUP))); return 1;
}

static int read_input(lua_State *L) {
    char buffer[65536];
    ssize_t n;
    do { n = read(STDIN_FILENO, buffer, sizeof(buffer)); } while (n < 0 && errno == EINTR);
    if (n < 0) return luaL_error(L, "leitura de stdin falhou");
    if (!n) lua_pushnil(L);
    else lua_pushlstring(L, buffer, (size_t)n);
    return 1;
}

/* The count hook belongs to this protected invocation. Disarm it in C before
 * returning either an error or results: a Lua-level cleanup can itself be
 * interrupted between pcall returning and debug.sethook(). */
static int protected_request(lua_State *L) {
    int status, count = lua_gettop(L);
    luaL_checktype(L, 1, LUA_TFUNCTION);
    status = lua_pcall(L, count - 1, LUA_MULTRET, 0);
    lua_sethook(L, NULL, 0, 0);
    count = lua_gettop(L);
    lua_pushboolean(L, status == LUA_OK);
    lua_insert(L, 1);
    return count + 1;
}

int luaopen_sls_nativo(lua_State *L) {
    static const luaL_Reg api[] = {
#if defined(SANTAFE_SLS_EMBUTIDO)
        {"sha256", hash_source},
#endif
        {"abraRaiz", open_root}, {"listeFontes", list_sources}, {"leiaFonte", read_source},
        {"entradaPronta", input_ready}, {"leiaEntrada", read_input},
        {"executeProtegido", protected_request}, {NULL, NULL}
    };
    if (luaL_newmetatable(L, "SLS.descritor")) {
        lua_pushcfunction(L, close_handle); lua_setfield(L, -2, LUA_MM_FINALIZE);
    }
    lua_pop(L, 1);
    if (luaL_newmetatable(L, "SLS.diretorio")) {
        lua_pushcfunction(L, close_directory); lua_setfield(L, -2, LUA_MM_FINALIZE);
    }
    lua_pop(L, 1); luaL_newlib(L, api); return 1;
}

#if defined(SANTAFE_DADOS_V3) && !defined(SANTAFE_SLS_EMBUTIDO)
SANTAFE_MODULE_ABI;
#endif
