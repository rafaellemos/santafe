#ifndef SELECT_H
#define SELECT_H
/*=========================================================================*\
* Select implementation
* LuaSocket toolkit
*
* Cada objeto passado a tomada.selecione() deve expor obterDescritor(),
* que devolve o descritor usado pela chamada de sistema. O método sujo()
* deve devolver verdadeiro quando já houver dados na memória intermediária.
\*=========================================================================*/

#ifndef _WIN32
#pragma GCC visibility push(hidden)
#endif

int select_open(lua_State *L);

#ifndef _WIN32
#pragma GCC visibility pop
#endif

#endif /* SELECT_H */
