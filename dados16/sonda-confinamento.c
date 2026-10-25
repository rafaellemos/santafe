/* Isolated adversarial experiment for handle-relative operations and strict process pins.
 * Every path created here is beneath the disposable CI fixture. */
#include "ferramentas/windows/arquivos.h"
#include <winioctl.h>
static void check(int ok,const char *what){if(!ok){fprintf(stderr,"FALHA %s Win32=%lu\n",what,GetLastError());exit(1);}printf("PASSOU %s\n",what);}
static int junction(HANDLE h,const wchar_t *dest){
 struct {ULONG tag;USHORT bytes,reserved;USHORT suboff,sublen,printoff,printlen;WCHAR text[WF_MAX];} r;
 DWORD got;memset(&r,0,sizeof(r));r.tag=IO_REPARSE_TAG_MOUNT_POINT;
 wcscpy(r.text,L"\\??\\");wcscat(r.text,dest);r.sublen=(USHORT)(wcslen(r.text)*2);r.printoff=r.sublen+2;r.bytes=8+r.sublen+4;
 return DeviceIoControl(h,FSCTL_SET_REPARSE_POINT,&r,r.bytes+8,NULL,0,&got,NULL)!=0;
}
static void rename_child(HANDLE h,HANDLE dir,const wchar_t *name,int *ok){
 size_t n=offsetof(FILE_RENAME_INFO,FileName)+(wcslen(name)+1)*2;FILE_RENAME_INFO *r=calloc(1,n);
 r->RootDirectory=dir;r->FileNameLength=(DWORD)(wcslen(name)*2);memcpy(r->FileName,name,r->FileNameLength);*ok=wf_rename(h,r,(DWORD)n);free(r);
}
int main(int argc,char **argv){
 wchar_t base[WF_MAX],outside[WF_MAX],path[WF_MAX],secret[WF_MAX],victim[WF_MAX];HANDLE dir,mutator,h;DWORD n;int ok;
 check(argc==2,"argumento fixture");check(wf_wide(argv[1],strlen(argv[1]),base,WF_MAX)>0,"fixture UTF8");
 check(CreateDirectoryW(base,NULL),"criar fixture exclusiva");wcscpy(outside,base);wcscat(outside,L"\\fora");check(CreateDirectoryW(outside,NULL),"fora somente na fixture");
 wcscpy(secret,outside);wcscat(secret,L"\\segredo");h=CreateFileW(secret,GENERIC_WRITE,0,NULL,CREATE_NEW,0,NULL);check(h!=INVALID_HANDLE_VALUE,"segredo sintético");check(WriteFile(h,"INTACTO",7,&n,NULL),"gravar segredo");CloseHandle(h);
 for(int mode=0;mode<2;mode++){
  swprintf(path,WF_MAX,L"%ls\\modo%d",base,mode);check(CreateDirectoryW(path,NULL),"diretorio teste");
  dir=wf_open(path,FILE_LIST_DIRECTORY|FILE_TRAVERSE|FILE_READ_ATTRIBUTES,FILE_SHARE_READ|(mode?FILE_SHARE_WRITE:0),OPEN_EXISTING,1,0);check(dir!=INVALID_HANDLE_VALUE,"fixar sem SHARE_DELETE");
  h=wf_at(dir,L"temp",GENERIC_WRITE|DELETE,0,CREATE_NEW,0,1);check(h!=INVALID_HANDLE_VALUE,"temporario relativo");check(WriteFile(h,"NOVO",4,&n,NULL)&&FlushFileBuffers(h),"sincronizar");rename_child(h,dir,L"final",&ok);
  printf("RENOMEACAO modo=%d ok=%d erro=%lu\n",mode,ok,GetLastError());if(mode)check(ok,"substituicao relativa funcional");
  FILE_DISPOSITION_INFO del={TRUE};SetFileInformationByHandle(h,FileDispositionInfo,&del,sizeof(del));CloseHandle(h);
  wcscpy(victim,path);wcscat(victim,L"-movido");check(!MoveFileW(path,victim),"ancestral nao renomeado");
  if(mode){
   WF original={0},strict={0};original.n=1;original.h[0]=dir;wcscpy(original.path,path);
   check(wf_strict(&strict,&original),"reabrir diretório por handle com proteção estrita");
   mutator=CreateFileW(path,GENERIC_WRITE,FILE_SHARE_READ|FILE_SHARE_WRITE,NULL,OPEN_EXISTING,FILE_FLAG_BACKUP_SEMANTICS|FILE_FLAG_OPEN_REPARSE_POINT,NULL);
   check(mutator==INVALID_HANDLE_VALUE,"pin de processo impede mutador");wf_close(&strict);
  }
  mutator=CreateFileW(path,GENERIC_WRITE,FILE_SHARE_READ|FILE_SHARE_WRITE,NULL,OPEN_EXISTING,FILE_FLAG_BACKUP_SEMANTICS|FILE_FLAG_OPEN_REPARSE_POINT,NULL);
  int mutated=mutator!=INVALID_HANDLE_VALUE&&junction(mutator,outside);printf("MUTACAO modo=%d feita=%d erro=%lu\n",mode,mutated,GetLastError());if(mutator!=INVALID_HANDLE_VALUE)CloseHandle(mutator);
  if(mode){
   check(mutated,"ataque de juncao realmente exercitado");
   WF original={0},strict={0};original.n=1;original.h[0]=dir;wcscpy(original.path,path);
   check(!wf_strict(&strict,&original),"processo recusa diretório já transformado em junção");wf_close(&strict);
  }
  h=wf_at(dir,L"segredo",GENERIC_READ,FILE_SHARE_READ,OPEN_EXISTING,0,1);check(h==INVALID_HANDLE_VALUE,"leitura nao alcança fora");
  h=wf_at(dir,L"victim",GENERIC_WRITE|DELETE,0,CREATE_NEW,0,1);
  if(h!=INVALID_HANDLE_VALUE){WriteFile(h,"NAO_VAZAR",9,&n,NULL);rename_child(h,dir,L"renomeado",&ok);CloseHandle(h);}
  wcscpy(victim,outside);wcscat(victim,L"\\victim");check(GetFileAttributesW(victim)==INVALID_FILE_ATTRIBUTES,"criação nao alcança fora");
  wcscpy(victim,outside);wcscat(victim,L"\\renomeado");check(GetFileAttributesW(victim)==INVALID_FILE_ATTRIBUTES,"rename nao alcança fora");
  WF_ENUM e={0};WIN32_FIND_DATAW item;int count=0;while((ok=wf_next(dir,&e,&item))>0){check(wcscmp(item.cFileName,L"segredo")!=0,"enumeração nao alcança fora");check(++count<20,"enumeração limitada");}check(ok==0,"enumeração por handle concluída");
  CloseHandle(dir);
 }
 h=CreateFileW(secret,GENERIC_READ,FILE_SHARE_READ,NULL,OPEN_EXISTING,0,NULL);char text[8]={0};check(h!=INVALID_HANDLE_VALUE&&ReadFile(h,text,7,&n,NULL)&&!strcmp(text,"INTACTO"),"segredo intacto");CloseHandle(h);
 puts("CONFINAMENTO_RELATIVO_COMPROVADO_NA_FIXTURE");return 0;
}
