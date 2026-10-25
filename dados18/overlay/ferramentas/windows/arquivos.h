/* Private Win32 capabilities. Local fixed NTFS volumes only. All ancestors
 * pinned without FILE_SHARE_DELETE; every component opened NO_REPARSE.
 * No path-based check followed by a later unpinned open. */
#ifndef SF_WINDOWS_FILES_H
#define SF_WINDOWS_FILES_H
#ifndef _WIN32_WINNT
#define _WIN32_WINNT 0x0A00
#endif
#include <windows.h>
#include <winternl.h>
#include <sddl.h>
#include <aclapi.h>
#include <bcrypt.h>
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
/* Directory write sharing permits atomic child replacement. Safety relies on
 * one-component handle-relative operations, never on re-resolving path.
 * Processes additionally acquire strict pins for their entire lifetime. */
#define WF_DIR_SHARE (FILE_SHARE_READ|FILE_SHARE_WRITE)
typedef struct { HANDLE h[WF_DEPTH]; unsigned n; wchar_t path[WF_MAX]; HANDLE lock, lock_parent, guard_file; } WF;
static void wf_close(WF *w) {
    DWORD e=GetLastError();
    if(w->lock && w->lock!=INVALID_HANDLE_VALUE) CloseHandle(w->lock);
    w->lock=NULL;
    if(w->lock_parent)CloseHandle(w->lock_parent);
    w->lock_parent=NULL;
    if(w->guard_file && w->guard_file!=INVALID_HANDLE_VALUE) {
        FILE_DISPOSITION_INFO remove={TRUE};
        SetFileInformationByHandle(w->guard_file,FileDispositionInfo,&remove,sizeof(remove));
        CloseHandle(w->guard_file);
    }
    w->guard_file=NULL;
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
    if(!k)return 0;
    out[k]=0;return k;
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
        ((directory>=0 && !!(st.dwFileAttributes&FILE_ATTRIBUTE_DIRECTORY)!=directory))||
        (single && !(st.dwFileAttributes&FILE_ATTRIBUTE_DIRECTORY) && st.nNumberOfLinks!=1)) {SetLastError(ERROR_ACCESS_DENIED);return 0;}
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
        if(wcslen(sid)<200) {
            swprintf(sddl,512,L"O:%lsD:P(A;OICI;FA;;;%ls)",sid,sid);
            ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl,SDDL_REVISION_1,&sd,NULL);
        }
    }
    if(sid)LocalFree(sid);
    free(user);CloseHandle(token);return sd;
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
/* Resolve exactly one component relative to an already verified directory.
 * Neither a mutable drive mapping nor an ancestor reparse point is traversed. */
static HANDLE wf_at(HANDLE parent,const wchar_t *name,DWORD access,DWORD share,DWORD disposition,int dir,int single) {
    typedef NTSTATUS (NTAPI *Create)(PHANDLE,ACCESS_MASK,POBJECT_ATTRIBUTES,PIO_STATUS_BLOCK,PLARGE_INTEGER,ULONG,ULONG,ULONG,ULONG,PVOID,ULONG);
    typedef ULONG (WINAPI *Error)(NTSTATUS);
    HMODULE nt=GetModuleHandleW(L"ntdll.dll");Create create=(Create)(void*)GetProcAddress(nt,"NtCreateFile");Error error=(Error)(void*)GetProcAddress(nt,"RtlNtStatusToDosError");
    OBJECT_ATTRIBUTES oa;UNICODE_STRING us;IO_STATUS_BLOCK io;HANDLE h=INVALID_HANDLE_VALUE;NTSTATUS st;PSECURITY_DESCRIPTOR sd=NULL;
    ULONG options=0x00200000|0x00000020; /* FILE_OPEN_REPARSE_POINT | FILE_SYNCHRONOUS_IO_NONALERT */
    ULONG disp=disposition==CREATE_NEW?2:disposition==OPEN_ALWAYS?3:1;
    if(!create||!error||!wf_component(name,wcslen(name))){SetLastError(ERROR_INVALID_NAME);return INVALID_HANDLE_VALUE;}
    if(disp!=1){sd=wf_security();if(!sd){SetLastError(ERROR_ACCESS_DENIED);return INVALID_HANDLE_VALUE;}}
    /* DIRECTORY_FILE only needed to create. Existing directories are checked
     * on their returned handle, without combining incompatible open options. */
    if(dir==1 && disp!=1)options|=1;
    if(dir==0)options|=0x40;
    memset(&oa,0,sizeof(oa));memset(&io,0,sizeof(io));us.Buffer=(PWSTR)name;us.Length=(USHORT)(wcslen(name)*2);us.MaximumLength=us.Length;
    oa.Length=sizeof(oa);oa.RootDirectory=parent;oa.ObjectName=&us;oa.Attributes=0x40;oa.SecurityDescriptor=sd;
    st=create(&h,access|SYNCHRONIZE|FILE_READ_ATTRIBUTES,&oa,&io,NULL,FILE_ATTRIBUTE_NORMAL,share,disp,options,NULL,0);
    if(sd)LocalFree(sd);
    if(st<0){SetLastError(error(st));return INVALID_HANDLE_VALUE;}
    if(!wf_info(h,dir,single)){DWORD e=GetLastError();CloseHandle(h);SetLastError(e);return INVALID_HANDLE_VALUE;}
    return h;
}
static int wf_rename(HANDLE file,FILE_RENAME_INFO *rename,DWORD size) {
    typedef NTSTATUS (NTAPI *Set)(HANDLE,PIO_STATUS_BLOCK,PVOID,ULONG,FILE_INFORMATION_CLASS);
    typedef ULONG (WINAPI *Error)(NTSTATUS);
    HMODULE nt=GetModuleHandleW(L"ntdll.dll");IO_STATUS_BLOCK io;NTSTATUS st;
    Set set=(Set)(void*)GetProcAddress(nt,"NtSetInformationFile");
    Error error=(Error)(void*)GetProcAddress(nt,"RtlNtStatusToDosError");
    if(!set||!error){SetLastError(ERROR_NOT_SUPPORTED);return 0;}
    memset(&io,0,sizeof(io));st=set(file,&io,rename,size,(FILE_INFORMATION_CLASS)10);
    if(st<0){SetLastError(error(st));return 0;}return 1;
}
/* Handle-relative directory enumeration. Buffer is Lua-owned, including on OOM. */
typedef struct { unsigned char data[65536]; DWORD offset; int started,more; } WF_ENUM;
static int wf_next(HANDLE dir,WF_ENUM *e,WIN32_FIND_DATAW *out) {
    FILE_ID_BOTH_DIR_INFO *info;DWORD n;
    if(!e->started || !e->more){
        FILE_INFO_BY_HANDLE_CLASS cls=e->started?FileIdBothDirectoryInfo:FileIdBothDirectoryRestartInfo;
        if(!GetFileInformationByHandleEx(dir,cls,e->data,sizeof(e->data)))return GetLastError()==ERROR_NO_MORE_FILES?0:-1;
        e->started=1;e->offset=0;
    }
    if(e->offset+offsetof(FILE_ID_BOTH_DIR_INFO,FileName)>sizeof(e->data)){SetLastError(ERROR_INVALID_DATA);return -1;}
    info=(FILE_ID_BOTH_DIR_INFO*)(e->data+e->offset);n=info->FileNameLength/2;
    if(info->FileNameLength%2||n>=MAX_PATH||e->offset+offsetof(FILE_ID_BOTH_DIR_INFO,FileName)+info->FileNameLength>sizeof(e->data)){SetLastError(ERROR_INVALID_DATA);return -1;}
    memset(out,0,sizeof(*out));out->dwFileAttributes=info->FileAttributes;memcpy(out->cFileName,info->FileName,info->FileNameLength);
    e->more=info->NextEntryOffset!=0;
    if(e->more){if(info->NextEntryOffset<offsetof(FILE_ID_BOTH_DIR_INFO,FileName)||e->offset+info->NextEntryOffset>=sizeof(e->data)){SetLastError(ERROR_INVALID_DATA);return -1;}e->offset+=info->NextEntryOffset;}
    return 1;
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
/* Subprocesses resolve cwd by name. Acquire strict directory pins using the
 * same one-component NT opens, and require the identities of ALL original
 * ancestors. Already-mutated roots and competing writer handles fail closed. */
static int wf_strict(WF *to,WF *from) {
    const wchar_t *end,*p; wchar_t component[256],guard[64]; unsigned i; HANDLE h; unsigned char nonce[16];
    if(!from->n || wcsncmp(from->path,L"\\\\?\\Volume{",11)) {SetLastError(ERROR_INVALID_NAME);return 0;}
    /* Share flags do NOT prevent FILE_WRITE_ATTRIBUTES reparse mutation.
     * NTFS refuses reparse conversion of a nonempty directory (MS-FSA).
     * Each ancestor already contains the next pinned child. Keep a private
     * undeletable child in the leaf as well, then revalidate the full chain. */
    if(BCryptGenRandom(NULL,nonce,sizeof(nonce),BCRYPT_USE_SYSTEM_PREFERRED_RNG)<0){SetLastError(ERROR_GEN_FAILURE);return 0;}
    wcscpy(guard,L".processo-");for(i=0;i<16;i++)swprintf(guard+9+2*i,3,L"%02x",nonce[i]);
    to->guard_file=wf_at(from->h[from->n-1],guard,GENERIC_READ|DELETE,0,CREATE_NEW,0,1);
    if(to->guard_file==INVALID_HANDLE_VALUE){to->guard_file=NULL;return 0;}
    end=wcschr(from->path+4,L'\\');if(!end){SetLastError(ERROR_INVALID_NAME);return 0;}
    memcpy(to->path,from->path,(end-from->path+1)*sizeof(wchar_t));to->path[end-from->path+1]=0;
    if(!wf_add(to,wf_open(to->path,FILE_LIST_DIRECTORY|FILE_READ_ATTRIBUTES,FILE_SHARE_READ,OPEN_EXISTING,1,0)))return 0;
    p=end+1;
    while(*p) {
        end=wcschr(p,L'\\');if(!end)end=p+wcslen(p);
        if(!wf_component(p,end-p) || !wf_append(to,p,end-p)){SetLastError(ERROR_INVALID_NAME);return 0;}
        memcpy(component,p,(end-p)*sizeof(wchar_t));component[end-p]=0;
        h=wf_at(to->h[to->n-1],component,FILE_LIST_DIRECTORY|FILE_TRAVERSE,FILE_SHARE_READ,OPEN_EXISTING,1,0);
        if(!wf_add(to,h))return 0;
        p=*end?end+1:end;
    }
    if(to->n!=from->n){SetLastError(ERROR_ACCESS_DENIED);return 0;}
    for(i=0;i<to->n;i++) {
        BY_HANDLE_FILE_INFORMATION a,b;
        if(!GetFileInformationByHandle(to->h[i],&a)||!GetFileInformationByHandle(from->h[i],&b))return 0;
        if(a.dwVolumeSerialNumber!=b.dwVolumeSerialNumber||a.nFileIndexHigh!=b.nFileIndexHigh||a.nFileIndexLow!=b.nFileIndexLow){SetLastError(ERROR_ACCESS_DENIED);return 0;}
    }return 1;
}
static int wf_walk(WF *w,const wchar_t *p,int create) {
    const wchar_t *end; wchar_t component[256];HANDLE h;
    while(*p) {
        end=wcschr(p,L'/');if(!end)end=p+wcslen(p);
        if(!wf_component(p,(size_t)(end-p))||!wf_append(w,p,(size_t)(end-p))){SetLastError(ERROR_INVALID_NAME);return 0;}
        memcpy(component,p,(end-p)*sizeof(wchar_t));component[end-p]=0;
        h=wf_at(w->h[w->n-1],component,FILE_LIST_DIRECTORY|FILE_TRAVERSE,WF_DIR_SHARE,create?OPEN_ALWAYS:OPEN_EXISTING,1,0);
        if(!wf_add(w,h))return 0;
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
    if(!wf_add(w,wf_open(w->path,FILE_LIST_DIRECTORY|FILE_READ_ATTRIBUTES,WF_DIR_SHARE,OPEN_EXISTING,1,0)))return 0;
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
    return wf_add(w,wf_at(w->h[w->n-1],leaf,access,share,OPEN_EXISTING,0,1));
}
static int wf_read(lua_State *L,WF *root,const char *s,size_t n,size_t limit) {
    WF *w; LARGE_INTEGER size;DWORD k;size_t used=0;char *buffer;
    if(!wf_file(L,root,s,n,GENERIC_READ,FILE_SHARE_READ,&w)) {wf_close(w);return wf_fail(L,"arquivo inacessivel ou inseguro");}
    if(!GetFileSizeEx(w->h[w->n-1],&size)||size.QuadPart<0||(uint64_t)size.QuadPart>limit){wf_close(w);SetLastError(ERROR_FILE_TOO_LARGE);return wf_fail(L,"arquivo excessivo");}
    buffer=lua_newuserdata(L,(size_t)size.QuadPart+1);
    while(used<(size_t)size.QuadPart+1) {
        if(!ReadFile(w->h[w->n-1],buffer+used,(DWORD)((size_t)size.QuadPart+1-used),&k,NULL)){wf_close(w);return wf_fail(L,"leitura falhou");}
        if(!k)break;
        used+=k;
    }
    wf_close(w);
    if(used!=(size_t)size.QuadPart){SetLastError(ERROR_RETRY);return wf_fail(L,"arquivo alterado");}
    lua_pushlstring(L,buffer,used);return 1;
}
#endif
