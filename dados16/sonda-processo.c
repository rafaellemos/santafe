#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
int main(int argc,char **argv){
 if(argc<2)return 2;
 if(!strcmp(argv[1],"args")){int i;for(i=2;i<argc;i++)printf("%s\n",argv[i]);return 0;}
 if(!strcmp(argv[1],"env")){printf("%s",getenv("SANTAFE_TEST_SECRET")?"VAZOU":"LIMPO");return 0;}
 if(!strcmp(argv[1],"sleep")){Sleep(5000);return 0;}
 if(!strcmp(argv[1],"flood")){char b[4096];memset(b,'x',sizeof(b));for(int i=0;i<10000;i++)fwrite(b,1,sizeof(b),stdout);return 0;}
 if(!strcmp(argv[1],"child")){Sleep(2000);FILE *f=fopen("descendente-vazou","wb");if(f){fputs("ERRO",f);fclose(f);}return 0;}
 if(!strcmp(argv[1],"tree")||!strcmp(argv[1],"treehold")){wchar_t path[8192],cmd[16384];STARTUPINFOW s={0};PROCESS_INFORMATION p;s.cb=sizeof(s);GetModuleFileNameW(NULL,path,8192);swprintf(cmd,16384,L"\"%ls\" child",path);if(!CreateProcessW(path,cmd,NULL,NULL,FALSE,0,NULL,NULL,&s,&p))return 3;CloseHandle(p.hProcess);CloseHandle(p.hThread);if(!strcmp(argv[1],"treehold"))Sleep(8000);return 0;}
 return 4;
}
