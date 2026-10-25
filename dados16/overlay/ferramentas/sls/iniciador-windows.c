/* Native SLS launcher: loads only the installation next to this executable.
 * No shell, PATH lookup, project autoload or LUA_INIT. */
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include "lua.h"
#include "lauxlib.h"
#include "lualib.h"
int main(void){wchar_t wide[8192];char path[24576],*slash,*name;DWORD n;lua_State *L;int rc;
 if(!SetDefaultDllDirectories(LOAD_LIBRARY_SEARCH_DEFAULT_DIRS))return 126;
 n=GetModuleFileNameW(NULL,wide,8192);if(!n||n>=8192||!WideCharToMultiByte(CP_UTF8,WC_ERR_INVALID_CHARS,wide,-1,path,sizeof(path),NULL,NULL))return 126;
 for(name=path;*name;name++)if(*name=='\\')*name='/';slash=strrchr(path,'/');if(!slash)return 126;*slash=0;
 slash=strrchr(path,'/');if(!slash)return 126;int checkout=!strcmp(slash+1,"src");*slash=0;
 if(strlen(path)>16000)return 126;strcat(path,checkout?"/ferramentas/sls/sls.f\xc3\xa9":"/share/santaf\xc3\xa9/1.0/ferramentas/sls/sls.f\xc3\xa9");
 L=luaL_newstate();if(!L)return 125;lua_pushboolean(L,1);lua_setfield(L,LUA_REGISTRYINDEX,"LUA_NOENV");luaL_openlibs(L);
 lua_newtable(L);lua_pushstring(L,path);lua_rawseti(L,-2,0);lua_setglobal(L,"arg");
 rc=luaL_loadfilex(L,path,"t");if(!rc)rc=lua_pcall(L,0,LUA_MULTRET,0);
 if(rc)fprintf(stderr,"SLS: %s\n",lua_tostring(L,-1));lua_close(L);return rc?1:0;
}
