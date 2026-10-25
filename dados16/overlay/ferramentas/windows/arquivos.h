/* Private Win32 capabilities. Local fixed NTFS volumes only. All ancestors
 * pinned without FILE_SHARE_DELETE; every component opened NO_REPARSE.
 * No path-based check followed by a later unpinned open. */
#ifndef SF_WINDOWS_FILES_H
#define SF_WINDOWS_FILES_H
#ifndef _WIN32_WINNT
#define _WIN32_WINNT 0x0A00
#endif
#include <windows.h>
#include <sddl.h>
#include <aclapi.h>
#include <wchar.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "lua.h"
#include "lauxlib.h"
#define WF_MT "Santafe.Win32.capacidade"
#define WF_MAX 8192
#define WF_DEPTH 96
typedef struct { HANDLE h[WF_DEPTH]; unsigned n; wchar_t path[WF_MAX]; HANDLE lock; } WF;
static void wf_close(WF *w) {
    DWORD e=GetLastError();
    if(w->lock && w->lock!=INVALID_HANDLE_VALUE) CloseHandle(w->lock);
    w->lock=NULL;
    while(w->n) CloseHandle(w->h[--w->n]);
    SetLastError(e);
}
static int wf_gc(lua_State *L) { wf_close(lua_touserdata(L,1)); return 0; }
static void wf_register(lua_State *L) {
    if(luaL_newmetatable(L,WF_MT)) {lua_pushcfunction(L,wf_gc);lua_setfield(L,-2,LUA_MM_FINALIZE);}
    lua_pop(L,1);
}
static WF *wf_new(lua_State *L) {
    WF *w=lua_newuserdata(L,sizeof(*w));memset(w,0,sizeof(*w));
    luaL_getmetatable(L,WF_MT);lua_setmetatable(L,-2);return w;
}
static int wf_fail(lua_State *L,const char *s) {
    DWORD e=GetLastError();lua_pushnil(L);lua_pushfstring(L,"%s (Win32 %d)",s,(int)e);lua_pushinteger(L,e);return 3;
}
static int wf_wide(const char *s,size_t n,wchar_t *out,int cap) {
    int k;if(!n || n>32760 || strlen(s)!=n){SetLastError(ERROR_INVALID_NAME);return 0;}
    k=MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,s,(int)n,out,cap-1);
    if(!k)return 0;out[k]=0;return k;
}
static int wf_utf8(const wchar_t *s,char *out,int cap) {
    return WideCharToMultiByte(CP_UTF8,WC_ERR_INVALID_CHARS,s,-1,out,cap,NULL,NULL);
}
static int wf_component(const wchar_t *s,size_t n) {
    size_t i,k=0; wchar_t base[256];
    if(!n || n>255 || s[n-1]==L'.' || s[n-1]==L' ')return 0;
    for(i=0;i<n;i++) {
        if(s[i]<32 || s[i]==127 || wcschr(L"\\/:*?\"<>|",s[i]))return 0;
        if(s[i]!=L'.' && k==i)base[k++]=s[i];
    }
    base[k]=0;
    if(!_wcsicmp(base,L"CON")||!_wcsicmp(base,L"PRN")||!_wcsicmp(base,L"AUX")||!_wcsicmp(base,L"NUL")||
       !_wcsicmp(base,L"CONIN$")||!_wcsicmp(base,L"CONOUT$"))return 0;
    if(k==4 && (!_wcsnicmp(base,L"COM",3)||!_wcsnicmp(base,L"LPT",3)) &&
        ((base[3]>=L'0'&&base[3]<=L'9')||base[3]==0xb9||base[3]==0xb2||base[3]==0xb3))return 0;
    return 1;
}
static int wf_relative(const char *s,size_t n,wchar_t out[WF_MAX]) {
    size_t i,start=0,len; if(n>2048 || !wf_wide(s,n,out,WF_MAX))return 0;
    len=wcslen(out);
    for(i=0;i<=len;i++) if(i==len||out[i]==L'/') {
        if(!wf_component(out+start,i-start)){SetLastError(ERROR_INVALID_NAME);return 0;}start=i+1;
    }
    return 1;
}
static int wf_info(HANDLE h,int directory,int single) {
    BY_HANDLE_FILE_INFORMATION st;
    if(GetFileType(h)!=FILE_TYPE_DISK || !GetFileInformationByHandle(h,&st))return 0;
    if((st.dwFileAttributes&FILE_ATTRIBUTE_REPARSE_POINT)||
        (!!(st.dwFileAttributes&FILE_ATTRIBUTE_DIRECTORY)!=directory)||
        (single && st.nNumberOfLinks!=1)) {SetLastError(ERROR_ACCESS_DENIED);return 0;}
    return 1;
}
/* Private new objects: protected DACL grants only the current token user. */
static PSECURITY_DESCRIPTOR wf_security(void) {
    HANDLE token; DWORD size=0; TOKEN_USER *user=NULL; LPWSTR sid=NULL;
    wchar_t sddl[512]; PSECURITY_DESCRIPTOR sd=NULL;
    if(!OpenProcessToken(GetCurrentProcess(),TOKEN_QUERY,&token))return NULL;
    GetTokenInformation(token,TokenUser,NULL,0,&size);
    if(size && (user=malloc(size)) && GetTokenInformation(token,TokenUser,user,size,&size) &&
       ConvertSidToStringSidW(user->User.Sid,&sid)) {
        if(wcslen(sid)<400) {
            swprintf(sddl,512,L"D:P(A;OICI;FA;;;%ls)",sid);
            ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl,SDDL_REVISION_1,&sd,NULL);
        }
    }
    if(sid)LocalFree(sid);free(user);CloseHandle(token);return sd;
}
static int wf_mkdir(const wchar_t *path) {
    PSECURITY_DESCRIPTOR sd=wf_security();SECURITY_ATTRIBUTES sa={sizeof(sa),sd,FALSE};BOOL ok;DWORD e;
    if(!sd){SetLastError(ERROR_ACCESS_DENIED);return 0;}
    ok=CreateDirectoryW(path,&sa);e=GetLastError();LocalFree(sd);SetLastError(e);return ok||e==ERROR_ALREADY_EXISTS;
}
static int wf_owner(HANDLE h) {
    HANDLE token;DWORD size=0;TOKEN_USER *u=NULL;PSID owner;PSECURITY_DESCRIPTOR sd=NULL;int same=0;
    if(GetSecurityInfo(h,SE_FILE_OBJECT,OWNER_SECURITY_INFORMATION,&owner,NULL,NULL,NULL,&sd)!=ERROR_SUCCESS)return 0;
    if(OpenProcessToken(GetCurrentProcess(),TOKEN_QUERY,&token)) {
        GetTokenInformation(token,TokenUser,NULL,0,&size);
        if(size && (u=malloc(size)) && GetTokenInformation(token,TokenUser,u,size,&size))same=EqualSid(owner,u->User.Sid);
        free(u);CloseHandle(token);
    }LocalFree(sd);if(!same)SetLastError(ERROR_ACCESS_DENIED);return same;
}
static HANDLE wf_open(const wchar_t *p,DWORD access,DWORD share,DWORD disposition,int dir,int single) {
    PSECURITY_DESCRIPTOR sd=NULL;SECURITY_ATTRIBUTES sa={sizeof(sa),NULL,FALSE};HANDLE h;DWORD error;
    if(disposition!=OPEN_EXISTING) {sd=wf_security();if(!sd){SetLastError(ERROR_ACCESS_DENIED);return INVALID_HANDLE_VALUE;}sa.lpSecurityDescriptor=sd;}
    h=CreateFileW(p,access,share,sd?&sa:NULL,disposition,FILE_FLAG_OPEN_REPARSE_POINT|FILE_FLAG_BACKUP_SEMANTICS,NULL);
    error=GetLastError();if(sd)LocalFree(sd);SetLastError(error);
    if(h!=INVALID_HANDLE_VALUE && !wf_info(h,dir,single)) {DWORD e=GetLastError();CloseHandle(h);SetLastError(e);return INVALID_HANDLE_VALUE;}
    return h;
}
static int wf_add(WF *w,HANDLE h) {
    if(h==INVALID_HANDLE_VALUE)return 0;
    if(w->n>=WF_DEPTH){CloseHandle(h);SetLastError(ERROR_BUFFER_OVERFLOW);return 0;}
    w->h[w->n++]=h;return 1;
}
static int wf_copy(WF *to,WF *from) {
    unsigned i;HANDLE h;
    if(!from->n){SetLastError(ERROR_INVALID_HANDLE);return 0;}
    wcscpy(to->path,from->path);
    for(i=0;i<from->n;i++) {
        if(!DuplicateHandle(GetCurrentProcess(),from->h[i],GetCurrentProcess(),&h,0,FALSE,DUPLICATE_SAME_ACCESS)||!wf_add(to,h))return 0;
    }return 1;
}
static int wf_append(WF *w,const wchar_t *s,size_t len) {
    size_t n=wcslen(w->path);
    if(n+len+2>=WF_MAX){SetLastError(ERROR_FILENAME_EXCED_RANGE);return 0;}
    if(n && w->path[n-1]!=L'\\')w->path[n++]=L'\\';
    memcpy(w->path+n,s,len*sizeof(wchar_t));w->path[n+len]=0;return 1;
}
static int wf_walk(WF *w,const wchar_t *p,int create) {
    const wchar_t *end;
    while(*p) {
        end=wcschr(p,L'/');if(!end)end=p+wcslen(p);
        if(!wf_component(p,(size_t)(end-p))||!wf_append(w,p,(size_t)(end-p))){SetLastError(ERROR_INVALID_NAME);return 0;}
        if(create && !wf_mkdir(w->path))return 0;
        if(!wf_add(w,wf_open(w->path,FILE_LIST_DIRECTORY|FILE_READ_ATTRIBUTES,FILE_SHARE_READ,OPEN_EXISTING,1,0)))return 0;
        p=*end?end+1:end;
    }return 1;
}
static int wf_root(WF *w,const char *s,size_t n) {
    wchar_t p[WF_MAX],volume[128],drive[4],fs[64];size_t i;
    if(n==1&&s[0]=='.') {if(!GetCurrentDirectoryW(WF_MAX,p))return 0;}
    else if(!wf_wide(s,n,p,WF_MAX))return 0;
    for(i=0;p[i];i++)if(p[i]==L'\\')p[i]=L'/';
    if(!((p[0]>=L'a'&&p[0]<=L'z')||(p[0]>=L'A'&&p[0]<=L'Z'))||p[1]!=L':'||p[2]!=L'/') {SetLastError(ERROR_INVALID_NAME);return 0;}
    drive[0]=p[0];drive[1]=L':';drive[2]=L'\\';drive[3]=0;
    if(GetDriveTypeW(drive)!=DRIVE_FIXED || !GetVolumeInformationW(drive,NULL,0,NULL,NULL,NULL,fs,64)||_wcsicmp(fs,L"NTFS")||
       !GetVolumeNameForVolumeMountPointW(drive,volume,128)){SetLastError(ERROR_NOT_SUPPORTED);return 0;}
    wcscpy(w->path,volume);
    if(!wf_add(w,wf_open(w->path,FILE_LIST_DIRECTORY|FILE_READ_ATTRIBUTES,FILE_SHARE_READ,OPEN_EXISTING,1,0)))return 0;
    return wf_walk(w,p+3,0);
}
static int wf_parent(WF *w,WF *root,const char *s,size_t n,wchar_t leaf[256],int create) {
    wchar_t path[WF_MAX],*last;
    if(!wf_relative(s,n,path)||!wf_copy(w,root))return 0;
    last=wcsrchr(path,L'/');wcscpy(leaf,last?last+1:path);
    if(last){*last=0;return wf_walk(w,path,create);}return 1;
}
static int wf_file(lua_State *L,WF *root,const char *s,size_t n,DWORD access,DWORD share,WF **owned) {
    wchar_t leaf[256];WF *w=wf_new(L);*owned=w;
    if(!wf_parent(w,root,s,n,leaf,0)||!wf_append(w,leaf,wcslen(leaf)))return 0;
    return wf_add(w,wf_open(w->path,access,share,OPEN_EXISTING,0,1));
}
static int wf_read(lua_State *L,WF *root,const char *s,size_t n,size_t limit) {
    WF *w; LARGE_INTEGER size;DWORD k;size_t used=0;char *buffer;
    if(!wf_file(L,root,s,n,GENERIC_READ,FILE_SHARE_READ,&w)) {wf_close(w);return wf_fail(L,"arquivo inacessivel ou inseguro");}
    if(!GetFileSizeEx(w->h[w->n-1],&size)||size.QuadPart<0||(uint64_t)size.QuadPart>limit){wf_close(w);SetLastError(ERROR_FILE_TOO_LARGE);return wf_fail(L,"arquivo excessivo");}
    buffer=lua_newuserdata(L,(size_t)size.QuadPart+1);
    while(used<(size_t)size.QuadPart+1) {
        if(!ReadFile(w->h[w->n-1],buffer+used,(DWORD)((size_t)size.QuadPart+1-used),&k,NULL)){wf_close(w);return wf_fail(L,"leitura falhou");}
        if(!k)break;used+=k;
    }
    wf_close(w);
    if(used!=(size_t)size.QuadPart){SetLastError(ERROR_RETRY);return wf_fail(L,"arquivo alterado");}
    lua_pushlstring(L,buffer,used);return 1;
}
#endif
