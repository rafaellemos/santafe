#define _WIN32_WINNT 0x0A00
#define UNICODE
#define _UNICODE
#include <windows.h>
#include <msi.h>
#include <msiquery.h>
#include <wchar.h>
#include <stdio.h>
#include <string.h>
static void logmsg(MSIHANDLE h,const wchar_t *s){MSIHANDLE r=MsiCreateRecord(1);MsiRecordSetStringW(r,0,s);MsiProcessMessage(h,INSTALLMESSAGE_INFO,r);MsiCloseHandle(r);}
static int prop(MSIHANDLE h,const wchar_t*n,wchar_t*b,DWORD size){return MsiGetPropertyW(h,n,b,&size)==ERROR_SUCCESS;}
static UINT refuse(MSIHANDLE h,const wchar_t*s){logmsg(h,s);return ERROR_INSTALL_FAILURE;}
static int tree_safe(const wchar_t *path,unsigned depth,unsigned *count){
 if(depth>32||wcslen(path)>900||*count>10000)return 0;
 wchar_t pattern[1024];swprintf(pattern,1024,L"%s\\*",path);WIN32_FIND_DATAW data;HANDLE find=FindFirstFileW(pattern,&data);
 if(find==INVALID_HANDLE_VALUE)return GetLastError()==ERROR_FILE_NOT_FOUND||GetLastError()==ERROR_PATH_NOT_FOUND;
 int safe=1;
 do{
  if(!wcscmp(data.cFileName,L".")||!wcscmp(data.cFileName,L".."))continue;
  if(++*count>10000||(data.dwFileAttributes&FILE_ATTRIBUTE_REPARSE_POINT)){safe=0;break;}
  wchar_t child[1200];swprintf(child,1200,L"%s\\%s",path,data.cFileName);
  if(data.dwFileAttributes&FILE_ATTRIBUTE_DIRECTORY){if(!tree_safe(child,depth+1,count)){safe=0;break;}}
  else{
   HANDLE file=CreateFileW(child,FILE_READ_ATTRIBUTES,FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE,NULL,OPEN_EXISTING,FILE_FLAG_OPEN_REPARSE_POINT,NULL);BY_HANDLE_FILE_INFORMATION info;
   if(file==INVALID_HANDLE_VALUE){safe=0;break;}
   int valid=GetFileInformationByHandle(file,&info)&&info.nNumberOfLinks==1&&!(info.dwFileAttributes&FILE_ATTRIBUTE_REPARSE_POINT);CloseHandle(file);if(!valid){safe=0;break;}
  }
 }while(FindNextFileW(find,&data));
 if(safe&&GetLastError()!=ERROR_NO_MORE_FILES)safe=0;
 FindClose(find);return safe;
}
__declspec(dllexport) UINT __stdcall ValidateTarget(MSIHANDLE h){
 wchar_t path[1024],base[1024],full[1024],standard[1024],prefix[1024],old[1024],installed[32],related[512],remove[32];
 if(!prop(h,L"REMOVE",remove,32))return ERROR_INSTALL_FAILURE;
 /* Uninstall also inspects the tree: a substituted junction must not
  * redirect removal of managed files into another directory. */
 int removing=!wcscmp(remove,L"ALL");
 /* MSI applies a version lie even to RtlGetVersion (6.3 on Server2022).
  * Probe the required Win10+ process attribute instead, without starting code. */
 SIZE_T bytes=0;InitializeProcThreadAttributeList(NULL,1,0,&bytes);
 LPPROC_THREAD_ATTRIBUTE_LIST attrs=HeapAlloc(GetProcessHeap(),0,bytes);HANDLE job=CreateJobObjectW(NULL,NULL);
 int initialized=attrs&&InitializeProcThreadAttributeList(attrs,1,0,&bytes);
 int supported=initialized&&job&&UpdateProcThreadAttribute(attrs,0,PROC_THREAD_ATTRIBUTE_JOB_LIST,&job,sizeof(job),NULL,NULL);
 if(initialized)DeleteProcThreadAttributeList(attrs);
 if(attrs)HeapFree(GetProcessHeap(),0,attrs);
 if(job)CloseHandle(job);
 if(!supported&&!removing)return refuse(h,L"DADOS20_JOB_LIST_ATTRIBUTE_REQUIRED");
 if(!prop(h,L"INSTALLDIR",path,1024)||!prop(h,L"LocalAppDataFolder",base,1024))return ERROR_INSTALL_FAILURE;
 if(wcslen(path)>230||wcslen(base)>900)return refuse(h,L"DADOS20_TARGET_PATH_TOO_LONG");
 if(wcslen(path)<3||path[1]!=L':'||path[2]!=L'\\')return refuse(h,L"DADOS20_TARGET_NOT_LOCAL");
 wchar_t drive[4]={path[0],L':',L'\\',0},fs[32];
 if(GetDriveTypeW(drive)!=DRIVE_FIXED||!GetVolumeInformationW(drive,NULL,0,NULL,NULL,NULL,fs,32)||_wcsicmp(fs,L"NTFS"))return refuse(h,L"DADOS20_TARGET_REQUIRES_FIXED_NTFS");
 swprintf(standard,1024,L"%sPrograms\\Santafe",base);
 swprintf(prefix,1024,L"%sPrograms\\Santafe-",base);
 if(!GetFullPathNameW(path,1024,full,NULL))return refuse(h,L"DADOS20_TARGET_OUTSIDE_USER_CHANNEL");
 size_t fulln=wcslen(full),standardn=wcslen(standard);
 int isstandard=!_wcsicmp(full,standard)||(fulln==standardn+1&&full[fulln-1]==L'\\'&&!_wcsnicmp(full,standard,standardn));
 if(!isstandard&&_wcsnicmp(full,prefix,wcslen(prefix)))return refuse(h,L"DADOS20_TARGET_OUTSIDE_USER_CHANNEL");
 if(_wcsicmp(path,full))return refuse(h,L"DADOS20_TARGET_NOT_CANONICAL");
 for(wchar_t *p=path+3;*p;p++){
  if(*p==L':'||*p<32)return refuse(h,L"DADOS20_TARGET_INVALID_COMPONENT");
  if(*p==L'\\'&&(p[-1]==L'.'||p[-1]==L' '))return refuse(h,L"DADOS20_TARGET_INVALID_COMPONENT");
 }
 /* Point-in-time preflight, not a sandbox against another process of the same user. */
 for(wchar_t *p=path+3;;p++)if(*p==L'\\'||!*p){
  wchar_t save=*p;*p=0;
  if(wcslen(path)>3){DWORD a=GetFileAttributesW(path);if(a!=INVALID_FILE_ATTRIBUTES){
   if((a&FILE_ATTRIBUTE_REPARSE_POINT)||!(a&FILE_ATTRIBUTE_DIRECTORY)){*p=save;return refuse(h,L"DADOS20_TARGET_REPARSE_OR_FILE");}
  }else if(GetLastError()!=ERROR_FILE_NOT_FOUND&&GetLastError()!=ERROR_PATH_NOT_FOUND){*p=save;return refuse(h,L"DADOS20_TARGET_INACCESSIBLE");}}
  *p=save;if(!save)break;
 }
 if(!prop(h,L"Installed",installed,32)||!prop(h,L"OLDERPRODUCTS",related,512)||!prop(h,L"OLDINSTALLDIR",old,1024))return ERROR_INSTALL_FAILURE;
 if(old[0]&&_wcsicmp(old,path))return refuse(h,L"DADOS20_TARGET_MOVE_REQUIRES_UNINSTALL");
 if(!installed[0]&&!related[0]){
  wchar_t pattern[1100];swprintf(pattern,1100,L"%s\\*",path);WIN32_FIND_DATAW data;HANDLE f=FindFirstFileW(pattern,&data);
  if(f!=INVALID_HANDLE_VALUE){do{if(wcscmp(data.cFileName,L".")&&wcscmp(data.cFileName,L"..")){FindClose(f);return refuse(h,L"DADOS20_TARGET_NOT_EMPTY");}}while(FindNextFileW(f,&data));FindClose(f);}
 }
 unsigned count=0;if(!tree_safe(path,0,&count))return refuse(h,L"DADOS20_TARGET_UNSAFE_ENTRY");
 logmsg(h,L"DADOS20_TARGET_PREFLIGHT_OK");return ERROR_SUCCESS;
}
__declspec(dllexport) UINT __stdcall AbortAfterFiles(MSIHANDLE h){
 wchar_t data[1200];if(!prop(h,L"CustomActionData",data,1200))return ERROR_INSTALL_FAILURE;
 wchar_t *sep=wcschr(data,L'|');if(!sep)return ERROR_INSTALL_FAILURE;*sep++=0;
 wchar_t filename[1200];swprintf(filename,1200,L"%s\\VERSAO-INSTALADOR.txt",data);
 HANDLE f=CreateFileW(filename,GENERIC_READ,FILE_SHARE_READ,NULL,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,NULL);
 if(f==INVALID_HANDLE_VALUE)return refuse(h,L"DADOS20_FAULT_WITHOUT_NEW_FILE");
 char b[100]={0},expected[100]={0};DWORD n=0;ReadFile(f,b,99,&n,NULL);CloseHandle(f);WideCharToMultiByte(CP_UTF8,0,sep,-1,expected,100,NULL,NULL);
 if(strcmp(b,expected))return refuse(h,L"DADOS20_FAULT_WRONG_VERSION");
 logmsg(h,L"DADOS20_FALHA_APOS_COPIA_CONFIRMADA");return ERROR_INSTALL_FAILURE;
}
