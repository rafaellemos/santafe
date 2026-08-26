#ifndef EXCEPT_H
#define EXCEPT_H

#include "luasocket.h"

#ifndef _WIN32
#pragma GCC visibility push(hidden)
#endif

int except_open(lua_State *L);

#ifndef _WIN32
#pragma GCC visibility pop
#endif

#endif
