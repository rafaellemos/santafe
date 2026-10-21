/*
** Unicode helpers shared by the core libraries.
** See Copyright Notice in lua.h
*/

#ifndef lunicode_h
#define lunicode_h

#include <stddef.h>

#include "lua.h"


/*
** Count extended grapheme clusters in a well-formed UTF-8 byte sequence.
** Returns 1 on success.  On failure, returns 0 and stores the one-based
** offset of the malformed byte in 'invalid'.
*/
LUAI_FUNC int luaU_graphemes (const char *s, size_t length,
                               size_t *count, size_t *invalid);

/* Byte length of the identifier prefix: [L_][LMN_]*, without normalization.
** Returns zero for an invalid start; malformed UTF-8 terminates the prefix.
*/
LUAI_FUNC size_t luaU_identifier (const char *s, size_t length);

#endif
