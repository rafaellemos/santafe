/*
** $Id: lstrlib.c,v 1.254.1.1 2017/04/19 17:29:57 roberto Exp $
** Standard library for string operations and pattern-matching
** See Copyright Notice in lua.h
*/

#define lstrlib_c
#define LUA_LIB

#include "lprefix.h"


#include <ctype.h>
#include <float.h>
#include <limits.h>
#include <locale.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "lua.h"

#include "lauxlib.h"
#include "lualib.h"



#include <stdlib.h> /* Para malloc e free */
#include "zlib.h"      /* O compilador vai achar na pasta libs/zlib */

/*
** maximum number of captures that a pattern can do during
** pattern-matching. This limit is arbitrary, but must fit in
** an unsigned char.
*/
#if !defined(LUA_MAXCAPTURES)
#define LUA_MAXCAPTURES		32
#endif


/* macro to 'unsign' a character */
#define uchar(c)	((unsigned char)(c))


/*
** Some sizes are better limited to fit in 'int', but must also fit in
** 'size_t'. (We assume that 'lua_Integer' cannot be smaller than 'int'.)
*/
#define MAX_SIZET	((size_t)(~(size_t)0))

#define MAXSIZE  \
	(sizeof(size_t) < sizeof(int) ? MAX_SIZET : (size_t)(INT_MAX))




static int str_len (lua_State *L) {
  size_t l;
  luaL_checklstring(L, 1, &l);
  lua_pushinteger(L, (lua_Integer)l);
  return 1;
}


/* translate a relative string position: negative means back from end */
static lua_Integer posrelat (lua_Integer pos, size_t len) {
  if (pos >= 0) return pos;
  else if (0u - (size_t)pos > len) return 0;
  else return (lua_Integer)len + pos + 1;
}


static int str_sub (lua_State *L) {
  size_t l;
  const char *s = luaL_checklstring(L, 1, &l);
  lua_Integer start = posrelat(luaL_checkinteger(L, 2), l);
  lua_Integer end = posrelat(luaL_optinteger(L, 3, -1), l);
  if (start < 1) start = 1;
  if (end > (lua_Integer)l) end = l;
  if (start <= end)
    lua_pushlstring(L, s + start - 1, (size_t)(end - start) + 1);
  else lua_pushliteral(L, "");
  return 1;
}


static int str_reverse (lua_State *L) {
  size_t l, i;
  luaL_Buffer b;
  const char *s = luaL_checklstring(L, 1, &l);
  char *p = luaL_buffinitsize(L, &b, l);
  for (i = 0; i < l; i++)
    p[i] = s[l - i - 1];
  luaL_pushresultsize(&b, l);
  return 1;
}


static int str_lower (lua_State *L) {
  size_t l;
  size_t i;
  luaL_Buffer b;
  const char *s = luaL_checklstring(L, 1, &l);
  char *p = luaL_buffinitsize(L, &b, l);
  for (i=0; i<l; i++)
    p[i] = tolower(uchar(s[i]));
  luaL_pushresultsize(&b, l);
  return 1;
}


static int str_upper (lua_State *L) {
  size_t l;
  size_t i;
  luaL_Buffer b;
  const char *s = luaL_checklstring(L, 1, &l);
  char *p = luaL_buffinitsize(L, &b, l);
  for (i=0; i<l; i++)
    p[i] = toupper(uchar(s[i]));
  luaL_pushresultsize(&b, l);
  return 1;
}


static int str_rep (lua_State *L) {
  size_t l, lsep;
  const char *s = luaL_checklstring(L, 1, &l);
  lua_Integer n = luaL_checkinteger(L, 2);
  const char *sep = luaL_optlstring(L, 3, "", &lsep);
  if (n <= 0) lua_pushliteral(L, "");
  else if (l + lsep < l || l + lsep > MAXSIZE / n)  /* may overflow? */
    return luaL_error(L, "colar resultante grande demais");
  else {
    size_t totallen = (size_t)n * l + (size_t)(n - 1) * lsep;
    luaL_Buffer b;
    char *p = luaL_buffinitsize(L, &b, totallen);
    while (n-- > 1) {  /* first n-1 copies (followed by separator) */
      memcpy(p, s, l * sizeof(char)); p += l;
      if (lsep > 0) {  /* empty 'memcpy' is not that cheap */
        memcpy(p, sep, lsep * sizeof(char));
        p += lsep;
      }
    }
    memcpy(p, s, l * sizeof(char));  /* last copy (not followed by separator) */
    luaL_pushresultsize(&b, totallen);
  }
  return 1;
}


static int str_byte (lua_State *L) {
  size_t l;
  const char *s = luaL_checklstring(L, 1, &l);
  lua_Integer posi = posrelat(luaL_optinteger(L, 2, 1), l);
  lua_Integer pose = posrelat(luaL_optinteger(L, 3, posi), l);
  int n, i;
  if (posi < 1) posi = 1;
  if (pose > (lua_Integer)l) pose = l;
  if (posi > pose) return 0;  /* empty interval; return no values */
  if (pose - posi >= INT_MAX)  /* arithmetic overflow? */
    return luaL_error(L, "corte do colar longo demais");
  n = (int)(pose -  posi) + 1;
  luaL_checkstack(L, n, "corte do colar longo demais");
  for (i=0; i<n; i++)
    lua_pushinteger(L, uchar(s[posi+i-1]));
  return n;
}


static int str_char (lua_State *L) {
  int n = lua_gettop(L);  /* number of arguments */
  int i;
  luaL_Buffer b;
  char *p = luaL_buffinitsize(L, &b, n);
  for (i=1; i<=n; i++) {
    lua_Integer c = luaL_checkinteger(L, i);
    luaL_argcheck(L, uchar(c) == c, i, "valor fora da faixa");
    p[i - 1] = uchar(c);
  }
  luaL_pushresultsize(&b, n);
  return 1;
}


static int writer (lua_State *L, const void *b, size_t size, void *B) {
  (void)L;
  luaL_addlstring((luaL_Buffer *) B, (const char *)b, size);
  return 0;
}


static int str_dump (lua_State *L) {
  luaL_Buffer b;
  int strip = lua_toboolean(L, 2);
  luaL_checktype(L, 1, LUA_TFUNCTION);
  lua_settop(L, 1);
  luaL_buffinit(L,&b);
  if (lua_dump(L, writer, &b, strip) != 0)
    return luaL_error(L, "n\xC3\xA3o foi poss\xC3\xADvel gerar o bin\xC3\xA1rio da fun\xC3\xA7\xC3\xA3o fornecida");
  luaL_pushresult(&b);
  return 1;
}



/*
** {======================================================
** PATTERN MATCHING
** =======================================================
*/


#define CAP_UNFINISHED	(-1)
#define CAP_POSITION	(-2)


typedef struct MatchState {
  const char *src_init;  /* init of source string */
  const char *src_end;  /* end ('\0') of source string */
  const char *p_end;  /* end ('\0') of pattern */
  lua_State *L;
  int matchdepth;  /* control for recursive depth (to avoid C stack overflow) */
  unsigned char level;  /* total number of captures (finished or unfinished) */
  struct {
    const char *init;
    ptrdiff_t len;
  } capture[LUA_MAXCAPTURES];
} MatchState;


/* recursive function */
static const char *match (MatchState *ms, const char *s, const char *p);


/* maximum recursion depth for 'match' */
#if !defined(MAXCCALLS)
#define MAXCCALLS	200
#endif


#define L_ESC		'%'
#define SPECIALS	"^$*+?.([%-"


static int check_capture (MatchState *ms, int l) {
  l -= '1';
  if (l < 0 || l >= ms->level || ms->capture[l].len == CAP_UNFINISHED)
    return luaL_error(ms->L, "\xC3\xADndice de captura inv\xC3\xA1lido %%%d", l + 1);
  return l;
}


static int capture_to_close (MatchState *ms) {
  int level = ms->level;
  for (level--; level>=0; level--)
    if (ms->capture[level].len == CAP_UNFINISHED) return level;
  return luaL_error(ms->L, "captura de padr\xC3\xA3o inv\xC3\xA1lido");
}


/* letras de classe válidas depois de '%n' (negação): %nl, %nc, %nd, %nm,
 * %nM, %np, %ne, %na, %nh, %nv, %nz */
static int neg_class_letter (int c) {
  switch (c) {
    case 'l': case 'c': case 'd': case 'm': case 'M':
    case 'p': case 'e': case 'a': case 'h': case 'v': case 'z':
      return 1;
    default:
      return 0;
  }
}


static const char *classend (MatchState *ms, const char *p) {
  switch (*p++) {
    case L_ESC: {
      if (p == ms->p_end)
        luaL_error(ms->L, "padr\xC3\xA3o mal formado (finaliza com '%%')");
      /* '%n' + letra de classe = negação (3 caracteres: % n letra) */
      if (*p == 'n' && p + 1 < ms->p_end && neg_class_letter(uchar(*(p + 1))))
        return p + 2;
      return p+1;
    }
    case '[': {
      if (*p == '^') p++;
      do {  /* look for a ']' */
        if (p == ms->p_end)
          luaL_error(ms->L, "padr\xC3\xA3o mal formado (faltando ']')");
        if (*(p++) == L_ESC && p < ms->p_end)
          p++;  /* skip escapes (e.g. '%]') */
      } while (*p != ']');
      return p+1;
    }
    default: {
      return p;
    }
  }
}


/*
** {======================================================
** SUPORTE A LETRAS ACENTUADAS (UTF-8) NAS CLASSES DE PADRÃO
**
** O motor de padrões anda byte a byte, mas uma letra acentuada ocupa 2
** bytes em UTF-8 ("á" = C3 A1). Sem tratamento, %l pararia no meio da
** palavra ("ação" -> só "a"). Como o Santafé é feito pra lusófonos, isso
** não serve.
**
** A solução: quando o byte atual é não-ASCII, voltamos até o byte líder da
** sequência, decodificamos o caractere inteiro e classificamos de verdade
** (letra? maiúscula? minúscula?). Cada byte da sequência responde pela
** classificação do caractere completo a que pertence — então %l+ atravessa
** a palavra acentuada inteira, byte a byte, sem precisar mudar o resto do
** motor.
** =======================================================
*/

/* Decodifica o caractere UTF-8 que contém o byte apontado por 's'. Se 's'
** cai num byte de continuação, volta até o líder. Devolve o codepoint, ou
** -1 se a sequência não for UTF-8 válido. */
static long utf8_codepoint_at (MatchState *ms, const char *s) {
  const char *p = s;
  unsigned char c;
  long cp;
  int extra;
  /* bytes de continuação são 10xxxxxx: volta até achar o líder */
  while (p > ms->src_init && (uchar(*p) & 0xC0) == 0x80)
    p--;
  c = uchar(*p);
  if (c < 0x80) return c;
  else if ((c & 0xE0) == 0xC0) { cp = c & 0x1F; extra = 1; }
  else if ((c & 0xF0) == 0xE0) { cp = c & 0x0F; extra = 2; }
  else if ((c & 0xF8) == 0xF0) { cp = c & 0x07; extra = 3; }
  else return -1;  /* byte de continuação solto/inválido */
  while (extra--) {
    p++;
    if (p >= ms->src_end || (uchar(*p) & 0xC0) != 0x80)
      return -1;  /* sequência truncada */
    cp = (cp << 6) | (uchar(*p) & 0x3F);
  }
  return cp;
}


/* Classifica um codepoint: 0 = não é letra, 'm' = minúscula,
** 'M' = maiúscula, 'l' = letra sem distinção de caixa. */
static int utf8_letter_case (long cp) {
  if (cp < 0) return 0;
  if (cp < 0x80) {  /* ASCII: usa a própria libc */
    if (islower((int)cp)) return 'm';
    if (isupper((int)cp)) return 'M';
    return isalpha((int)cp) ? 'l' : 0;
  }
  /* Latin-1 Suplementar (cobre português, espanhol, francês, alemão...) */
  if (cp >= 0x00C0 && cp <= 0x00FF) {
    if (cp == 0x00D7 || cp == 0x00F7) return 0;  /* × e ÷ não são letras */
    return (cp <= 0x00DE) ? 'M' : 'm';           /* 0xDF (ß) em diante: minúsculas */
  }
  /* Latin Estendido-A: maiúscula/minúscula alternam, em blocos */
  if (cp >= 0x0100 && cp <= 0x017F) {
    if (cp == 0x0138 || cp == 0x0149 || cp == 0x017F) return 'm';
    if (cp == 0x0178) return 'M';
    if (cp <= 0x0137 || (cp >= 0x014A && cp <= 0x0177))
      return (cp % 2 == 0) ? 'M' : 'm';
    return (cp % 2 == 0) ? 'm' : 'M';  /* 0x0139-0x0148 e 0x0179-0x017E */
  }
  /* Latin Estendido-B e Grego/Cirílico básicos: trata como letra, sem caixa */
  if ((cp >= 0x0180 && cp <= 0x024F) ||
      (cp >= 0x0370 && cp <= 0x03FF) ||
      (cp >= 0x0400 && cp <= 0x04FF))
    return 'l';
  return 0;  /* emoji, símbolos, pontuação "inteligente", etc. */
}


/* Classes de padrão do Santafé — cada letra é uma classe própria e
 * independente (não existe mais "maiúscula = complemento automático" como
 * no Lua original). Pra negar qualquer classe, use o prefixo '%n' + letra
 * (ex.: %nm = não-minúscula) — veja neg_class_letter/singlematch. */
static int match_class (int c, int cl) {
  switch (cl) {
    case 'l' : return isalpha(c);    /* letras */
    case 'c' : return iscntrl(c);    /* controle */
    case 'd' : return isdigit(c);    /* dígitos */
    case 'm' : return islower(c);    /* minúsculas */
    case 'M' : return isupper(c);    /* maiúsculas */
    case 'p' : return ispunct(c);    /* pontuação */
    case 'e' : return isspace(c);    /* espaço */
    case 'a' : return isalnum(c);    /* alfanumérico */
    case 'h' : return isxdigit(c);   /* hexadecimal */
    case 'v' : return isgraph(c);    /* visíveis */
    case 'z' : return (c == 0);      /* taco zero (opção obsoleta) */
    default: return (cl == c);
  }
}


/* Versão consciente de UTF-8, usada onde temos o ponteiro pro texto (e
** portanto dá pra decodificar o caractere inteiro). As classes de letra
** (%l, %m, %M, %a) enxergam acento; as outras seguem byte a byte. */
static int match_class_at (MatchState *ms, const char *s, int cl) {
  int c = uchar(*s);
  if (c < 0x80)  /* ASCII: caminho rápido, comportamento de sempre */
    return match_class(c, cl);
  switch (cl) {
    case 'l': return utf8_letter_case(utf8_codepoint_at(ms, s)) != 0;
    case 'm': return utf8_letter_case(utf8_codepoint_at(ms, s)) == 'm';
    case 'M': return utf8_letter_case(utf8_codepoint_at(ms, s)) == 'M';
    /* letra acentuada também conta como alfanumérico */
    case 'a': return utf8_letter_case(utf8_codepoint_at(ms, s)) != 0;
    case 'v': return 1;   /* todo caractere não-ASCII é visível */
    case 'c': return 0;   /* ...e não é controle, */
    case 'e': return 0;   /* nem espaço, */
    case 'd': case 'h': return 0;  /* nem dígito/hexadecimal */
    default: return match_class(c, cl);
  }
}


static int matchbracketclass (MatchState *ms, const char *sp, int c,
                              const char *p, const char *ec) {
  int sig = 1;
  if (*(p+1) == '^') {
    sig = 0;
    p++;  /* skip the '^' */
  }
  while (++p < ec) {
    if (*p == L_ESC) {
      p++;
      if (*p == 'n' && p + 1 < ec && neg_class_letter(uchar(*(p + 1)))) {
        p++;  /* aponta pra letra da classe (depois do 'n' de negação) */
        if (!(sp ? match_class_at(ms, sp, uchar(*p)) : match_class(c, uchar(*p))))
          return sig;
      }
      else if (sp ? match_class_at(ms, sp, uchar(*p)) : match_class(c, uchar(*p)))
        return sig;
    }
    else if ((*(p+1) == '-') && (p+2 < ec)) {
      p+=2;
      if (uchar(*(p-2)) <= c && c <= uchar(*p))
        return sig;
    }
    else if (uchar(*p) == c) return sig;
  }
  return !sig;
}


static int singlematch (MatchState *ms, const char *s, const char *p,
                        const char *ep) {
  if (s >= ms->src_end)
    return 0;
  else {
    int c = uchar(*s);
    switch (*p) {
      case '.': return 1;  /* matches any char */
      case L_ESC: {
        if (*(p+1) == 'n' && neg_class_letter(uchar(*(p+2))))
          return !match_class_at(ms, s, uchar(*(p+2)));
        return match_class_at(ms, s, uchar(*(p+1)));
      }
      case '[': return matchbracketclass(ms, s, c, p, ep-1);
      default:  return (uchar(*p) == c);
    }
  }
}


static const char *matchbalance (MatchState *ms, const char *s,
                                   const char *p) {
  if (p >= ms->p_end - 1)
    luaL_error(ms->L, "padr\xC3\xA3o mal formado (faltando argumentos para '%%b')");
  if (*s != *p) return NULL;
  else {
    int b = *p;
    int e = *(p+1);
    int cont = 1;
    while (++s < ms->src_end) {
      if (*s == e) {
        if (--cont == 0) return s+1;
      }
      else if (*s == b) cont++;
    }
  }
  return NULL;  /* string ends out of balance */
}


static const char *max_expand (MatchState *ms, const char *s,
                                 const char *p, const char *ep) {
  ptrdiff_t i = 0;  /* counts maximum expand for item */
  while (singlematch(ms, s + i, p, ep))
    i++;
  /* keeps trying to match with the maximum repetitions */
  while (i>=0) {
    const char *res = match(ms, (s+i), ep+1);
    if (res) return res;
    i--;  /* else didn't match; reduce 1 repetition to try again */
  }
  return NULL;
}


static const char *min_expand (MatchState *ms, const char *s,
                                 const char *p, const char *ep) {
  for (;;) {
    const char *res = match(ms, s, ep+1);
    if (res != NULL)
      return res;
    else if (singlematch(ms, s, p, ep))
      s++;  /* try with one more repetition */
    else return NULL;
  }
}


static const char *start_capture (MatchState *ms, const char *s,
                                    const char *p, int what) {
  const char *res;
  int level = ms->level;
  if (level >= LUA_MAXCAPTURES) luaL_error(ms->L, "muitas capturas");
  ms->capture[level].init = s;
  ms->capture[level].len = what;
  ms->level = level+1;
  if ((res=match(ms, s, p)) == NULL)  /* match failed? */
    ms->level--;  /* undo capture */
  return res;
}


static const char *end_capture (MatchState *ms, const char *s,
                                  const char *p) {
  int l = capture_to_close(ms);
  const char *res;
  ms->capture[l].len = s - ms->capture[l].init;  /* close capture */
  if ((res = match(ms, s, p)) == NULL)  /* match failed? */
    ms->capture[l].len = CAP_UNFINISHED;  /* undo capture */
  return res;
}


static const char *match_capture (MatchState *ms, const char *s, int l) {
  size_t len;
  l = check_capture(ms, l);
  len = ms->capture[l].len;
  if ((size_t)(ms->src_end-s) >= len &&
      memcmp(ms->capture[l].init, s, len) == 0)
    return s+len;
  else return NULL;
}


static const char *match (MatchState *ms, const char *s, const char *p) {
  if (ms->matchdepth-- == 0)
    luaL_error(ms->L, "padr\xC3\xA3o muito complexo");
  init: /* using goto's to optimize tail recursion */
  if (p != ms->p_end) {  /* end of pattern? */
    switch (*p) {
      case '(': {  /* start capture */
        if (*(p + 1) == ')')  /* position capture? */
          s = start_capture(ms, s, p + 2, CAP_POSITION);
        else
          s = start_capture(ms, s, p + 1, CAP_UNFINISHED);
        break;
      }
      case ')': {  /* end capture */
        s = end_capture(ms, s, p + 1);
        break;
      }
      case '$': {
        if ((p + 1) != ms->p_end)  /* is the '$' the last char in pattern? */
          goto dflt;  /* no; go to default */
        s = (s == ms->src_end) ? s : NULL;  /* check end of string */
        break;
      }
      case L_ESC: {  /* escaped sequences not in the format class[*+?-]? */
        switch (*(p + 1)) {
          case 'b': {  /* balanced string? */
            s = matchbalance(ms, s, p + 2);
            if (s != NULL) {
              p += 4; goto init;  /* return match(ms, s, p + 4); */
            }  /* else fail (s == NULL) */
            break;
          }
          case 'f': {  /* frontier? */
            const char *ep; char previous;
            p += 2;
            if (*p != '[')
              luaL_error(ms->L, "faltando '[' depois de  '%%f' no padr\xC3\xA3o");
            ep = classend(ms, p);  /* points to what is next */
            previous = (s == ms->src_init) ? '\0' : *(s - 1);
            if (!matchbracketclass(ms, NULL, uchar(previous), p, ep - 1) &&
               matchbracketclass(ms, s, uchar(*s), p, ep - 1)) {
              p = ep; goto init;  /* return match(ms, s, ep); */
            }
            s = NULL;  /* match failed */
            break;
          }
          case '0': case '1': case '2': case '3':
          case '4': case '5': case '6': case '7':
          case '8': case '9': {  /* capture results (%0-%9)? */
            s = match_capture(ms, s, uchar(*(p + 1)));
            if (s != NULL) {
              p += 2; goto init;  /* return match(ms, s, p + 2) */
            }
            break;
          }
          default: goto dflt;
        }
        break;
      }
      default: dflt: {  /* pattern class plus optional suffix */
        const char *ep = classend(ms, p);  /* points to optional suffix */
        /* does not match at least once? */
        if (!singlematch(ms, s, p, ep)) {
          if (*ep == '*' || *ep == '?' || *ep == '-') {  /* accept empty? */
            p = ep + 1; goto init;  /* return match(ms, s, ep + 1); */
          }
          else  /* '+' or no suffix */
            s = NULL;  /* fail */
        }
        else {  /* matched once */
          switch (*ep) {  /* handle optional suffix */
            case '?': {  /* optional */
              const char *res;
              if ((res = match(ms, s + 1, ep + 1)) != NULL)
                s = res;
              else {
                p = ep + 1; goto init;  /* else return match(ms, s, ep + 1); */
              }
              break;
            }
            case '+':  /* 1 or more repetitions */
              s++;  /* 1 match already done */
              /* FALLTHROUGH */
            case '*':  /* 0 or more repetitions */
              s = max_expand(ms, s, p, ep);
              break;
            case '-':  /* 0 or more repetitions (minimum) */
              s = min_expand(ms, s, p, ep);
              break;
            default:  /* no suffix */
              s++; p = ep; goto init;  /* return match(ms, s + 1, ep); */
          }
        }
        break;
      }
    }
  }
  ms->matchdepth++;
  return s;
}



static const char *lmemfind (const char *s1, size_t l1,
                               const char *s2, size_t l2) {
  if (l2 == 0) return s1;  /* empty strings are everywhere */
  else if (l2 > l1) return NULL;  /* avoids a negative 'l1' */
  else {
    const char *init;  /* to search for a '*s2' inside 's1' */
    l2--;  /* 1st char will be checked by 'memchr' */
    l1 = l1-l2;  /* 's2' cannot be found after that */
    while (l1 > 0 && (init = (const char *)memchr(s1, *s2, l1)) != NULL) {
      init++;   /* 1st char is already checked */
      if (memcmp(init, s2+1, l2) == 0)
        return init-1;
      else {  /* correct 'l1' and 's1' to try again */
        l1 -= init-s1;
        s1 = init;
      }
    }
    return NULL;  /* not found */
  }
}


static void push_onecapture (MatchState *ms, int i, const char *s,
                                                    const char *e) {
  if (i >= ms->level) {
    if (i == 0)  /* ms->level == 0, too */
      lua_pushlstring(ms->L, s, e - s);  /* add whole match */
    else
      luaL_error(ms->L, "\xC3\xADndice de captura inv\xC3\xA1lido %%%d", i + 1);
  }
  else {
    ptrdiff_t l = ms->capture[i].len;
    if (l == CAP_UNFINISHED) luaL_error(ms->L, "captura n\xC3\xA3o finalizada");
    if (l == CAP_POSITION)
      lua_pushinteger(ms->L, (ms->capture[i].init - ms->src_init) + 1);
    else
      lua_pushlstring(ms->L, ms->capture[i].init, l);
  }
}


static int push_captures (MatchState *ms, const char *s, const char *e) {
  int i;
  int nlevels = (ms->level == 0 && s) ? 1 : ms->level;
  luaL_checkstack(ms->L, nlevels, "capturas demais");
  for (i = 0; i < nlevels; i++)
    push_onecapture(ms, i, s, e);
  return nlevels;  /* number of strings pushed */
}


/* check whether pattern has no special characters */
static int nospecials (const char *p, size_t l) {
  size_t upto = 0;
  do {
    if (strpbrk(p + upto, SPECIALS))
      return 0;  /* pattern has a special character */
    upto += strlen(p + upto) + 1;  /* may have more after \0 */
  } while (upto <= l);
  return 1;  /* no special chars found */
}


static void prepstate (MatchState *ms, lua_State *L,
                       const char *s, size_t ls, const char *p, size_t lp) {
  ms->L = L;
  ms->matchdepth = MAXCCALLS;
  ms->src_init = s;
  ms->src_end = s + ls;
  ms->p_end = p + lp;
}


static void reprepstate (MatchState *ms) {
  ms->level = 0;
  lua_assert(ms->matchdepth == MAXCCALLS);
}


static int str_find_aux (lua_State *L, int find) {
  size_t ls, lp;
  const char *s = luaL_checklstring(L, 1, &ls);
  const char *p = luaL_checklstring(L, 2, &lp);
  lua_Integer init = posrelat(luaL_optinteger(L, 3, 1), ls);
  if (init < 1) init = 1;
  else if (init > (lua_Integer)ls + 1) {  /* start after string's end? */
    lua_pushnil(L);  /* cannot find anything */
    return 1;
  }
  /* explicit request or no special characters? */
  if (find && (lua_toboolean(L, 4) || nospecials(p, lp))) {
    /* do a plain search */
    const char *s2 = lmemfind(s + init - 1, ls - (size_t)init + 1, p, lp);
    if (s2) {
      lua_pushinteger(L, (s2 - s) + 1);
      lua_pushinteger(L, (s2 - s) + lp);
      return 2;
    }
  }
  else {
    MatchState ms;
    const char *s1 = s + init - 1;
    int anchor = (*p == '^');
    if (anchor) {
      p++; lp--;  /* skip anchor character */
    }
    prepstate(&ms, L, s, ls, p, lp);
    do {
      const char *res;
      reprepstate(&ms);
      if ((res=match(&ms, s1, p)) != NULL) {
        if (find) {
          lua_pushinteger(L, (s1 - s) + 1);  /* start */
          lua_pushinteger(L, res - s);   /* end */
          return push_captures(&ms, NULL, 0) + 2;
        }
        else
          return push_captures(&ms, s1, res);
      }
    } while (s1++ < ms.src_end && !anchor);
  }
  lua_pushnil(L);  /* not found */
  return 1;
}


static int str_find (lua_State *L) {
  return str_find_aux(L, 1);
}


static int str_match (lua_State *L) {
  return str_find_aux(L, 0);
}


/* state for 'gmatch' */
typedef struct GMatchState {
  const char *src;  /* current position */
  const char *p;  /* pattern */
  const char *lastmatch;  /* end of last match */
  MatchState ms;  /* match state */
} GMatchState;


static int gmatch_aux (lua_State *L) {
  GMatchState *gm = (GMatchState *)lua_touserdata(L, lua_upvalueindex(3));
  const char *src;
  gm->ms.L = L;
  for (src = gm->src; src <= gm->ms.src_end; src++) {
    const char *e;
    reprepstate(&gm->ms);
    if ((e = match(&gm->ms, src, gm->p)) != NULL && e != gm->lastmatch) {
      gm->src = gm->lastmatch = e;
      return push_captures(&gm->ms, src, e);
    }
  }
  return 0;  /* not found */
}


static int gmatch (lua_State *L) {
  size_t ls, lp;
  const char *s = luaL_checklstring(L, 1, &ls);
  const char *p = luaL_checklstring(L, 2, &lp);
  GMatchState *gm;
  lua_settop(L, 2);  /* keep them on closure to avoid being collected */
  gm = (GMatchState *)lua_newuserdata(L, sizeof(GMatchState));
  prepstate(&gm->ms, L, s, ls, p, lp);
  gm->src = s; gm->p = p; gm->lastmatch = NULL;
  lua_pushcclosure(L, gmatch_aux, 3);
  return 1;
}


static void add_s (MatchState *ms, luaL_Buffer *b, const char *s,
                                                   const char *e) {
  size_t l, i;
  lua_State *L = ms->L;
  const char *news = lua_tolstring(L, 3, &l);
  for (i = 0; i < l; i++) {
    if (news[i] != L_ESC)
      luaL_addchar(b, news[i]);
    else {
      i++;  /* skip ESC */
      if (!isdigit(uchar(news[i]))) {
        if (news[i] != L_ESC)
          luaL_error(L, "uso inv\xC3\xA1lido de '%c' no colar de substitui\xC3\xA7\xC3\xA3o", L_ESC);
        luaL_addchar(b, news[i]);
      }
      else if (news[i] == '0')
          luaL_addlstring(b, s, e - s);
      else {
        push_onecapture(ms, news[i] - '1', s, e);
        luaL_tolstring(L, -1, NULL);  /* if number, convert it to string */
        lua_remove(L, -2);  /* remove original value */
        luaL_addvalue(b);  /* add capture to accumulated result */
      }
    }
  }
}


static void add_value (MatchState *ms, luaL_Buffer *b, const char *s,
                                       const char *e, int tr) {
  lua_State *L = ms->L;
  switch (tr) {
    case LUA_TFUNCTION: {
      int n;
      lua_pushvalue(L, 3);
      n = push_captures(ms, s, e);
      lua_call(L, n, 1);
      break;
    }
    case LUA_TTABLE: {
      push_onecapture(ms, 0, s, e);
      lua_gettable(L, 3);
      break;
    }
    default: {  /* LUA_TNUMBER or LUA_TSTRING */
      add_s(ms, b, s, e);
      return;
    }
  }
  if (!lua_toboolean(L, -1)) {  /* nil or false? */
    lua_pop(L, 1);
    lua_pushlstring(L, s, e - s);  /* keep original text */
  }
  else if (!lua_isstring(L, -1))
    luaL_error(L, "valor de substitui\xC3\xA7\xC3\xA3o inv\xC3\xA1lido (%s)", luaL_typename(L, -1));
  luaL_addvalue(b);  /* add result to accumulator */
}


static int str_gsub (lua_State *L) {
  size_t srcl, lp;
  const char *src = luaL_checklstring(L, 1, &srcl);  /* subject */
  const char *p = luaL_checklstring(L, 2, &lp);  /* pattern */
  const char *lastmatch = NULL;  /* end of last match */
  int tr = lua_type(L, 3);  /* replacement type */
  lua_Integer max_s = luaL_optinteger(L, 4, srcl + 1);  /* max replacements */
  int anchor = (*p == '^');
  lua_Integer n = 0;  /* replacement count */
  MatchState ms;
  luaL_Buffer b;
  luaL_argcheck(L, tr == LUA_TNUMBER || tr == LUA_TSTRING ||
                   tr == LUA_TFUNCTION || tr == LUA_TTABLE, 3,
                      "esperado colar/fun\xC3\xA7\xC3\xA3o/tabela");
  luaL_buffinit(L, &b);
  if (anchor) {
    p++; lp--;  /* skip anchor character */
  }
  prepstate(&ms, L, src, srcl, p, lp);
  while (n < max_s) {
    const char *e;
    reprepstate(&ms);  /* (re)prepare state for new match */
    if ((e = match(&ms, src, p)) != NULL && e != lastmatch) {  /* match? */
      n++;
      add_value(&ms, &b, src, e, tr);  /* add replacement to buffer */
      src = lastmatch = e;
    }
    else if (src < ms.src_end)  /* otherwise, skip one character */
      luaL_addchar(&b, *src++);
    else break;  /* end of subject */
    if (anchor) break;
  }
  luaL_addlstring(&b, src, ms.src_end-src);
  luaL_pushresult(&b);
  lua_pushinteger(L, n);  /* number of substitutions */
  return 2;
}

/* }====================================================== */



/*
** {======================================================
** STRING FORMAT
** =======================================================
*/

#if !defined(lua_number2strx)	/* { */

/*
** Hexadecimal floating-point formatter
*/

#include <math.h>

#define SIZELENMOD	(sizeof(LUA_NUMBER_FRMLEN)/sizeof(char))


/*
** Number of bits that goes into the first digit. It can be any value
** between 1 and 4; the following definition tries to align the number
** to nibble boundaries by making what is left after that first digit a
** multiple of 4.
*/
#define L_NBFD		((l_mathlim(MANT_DIG) - 1)%4 + 1)


/*
** Add integer part of 'x' to buffer and return new 'x'
*/
static lua_Number adddigit (char *buff, int n, lua_Number x) {
  lua_Number dd = l_mathop(floor)(x);  /* get integer part from 'x' */
  int d = (int)dd;
  buff[n] = (d < 10 ? d + '0' : d - 10 + 'a');  /* add to buffer */
  return x - dd;  /* return what is left */
}


static int num2straux (char *buff, int sz, lua_Number x) {
  /* if 'inf' or 'NaN', format it like '%g' */
  if (x != x || x == (lua_Number)HUGE_VAL || x == -(lua_Number)HUGE_VAL)
    return l_sprintf(buff, sz, LUA_NUMBER_FMT, (LUAI_UACNUMBER)x);
  else if (x == 0) {  /* can be -0... */
    /* create "0" or "-0" followed by exponent */
    return l_sprintf(buff, sz, LUA_NUMBER_FMT "x0p+0", (LUAI_UACNUMBER)x);
  }
  else {
    int e;
    lua_Number m = l_mathop(frexp)(x, &e);  /* 'x' fraction and exponent */
    int n = 0;  /* character count */
    if (m < 0) {  /* is number negative? */
      buff[n++] = '-';  /* add signal */
      m = -m;  /* make it positive */
    }
    buff[n++] = '0'; buff[n++] = 'x';  /* add "0x" */
    m = adddigit(buff, n++, m * (1 << L_NBFD));  /* add first digit */
    e -= L_NBFD;  /* this digit goes before the radix point */
    if (m > 0) {  /* more digits? */
      buff[n++] = lua_getlocaledecpoint();  /* add radix point */
      do {  /* add as many digits as needed */
        m = adddigit(buff, n++, m * 16);
      } while (m > 0);
    }
    n += l_sprintf(buff + n, sz - n, "p%+d", e);  /* add exponent */
    lua_assert(n < sz);
    return n;
  }
}


static int lua_number2strx (lua_State *L, char *buff, int sz,
                            const char *fmt, lua_Number x) {
  int n = num2straux(buff, sz, x);
  if (fmt[SIZELENMOD] == 'A') {
    int i;
    for (i = 0; i < n; i++)
      buff[i] = toupper(uchar(buff[i]));
  }
  else if (fmt[SIZELENMOD] != 'a')
    return luaL_error(L, "modificadores para o formato '%%a'/'%%A' n\xC3\xA3o implementados");
  return n;
}

#endif				/* } */


/*
** Maximum size of each formatted item. This maximum size is produced
** by format('%.99f', -maxfloat), and is equal to 99 + 3 ('-', '.',
** and '\0') + number of decimal digits to represent maxfloat (which
** is maximum exponent + 1). (99+3+1 then rounded to 120 for "extra
** expenses", such as locale-dependent stuff)
*/
#define MAX_ITEM        (120 + l_mathlim(MAX_10_EXP))


/* valid flags in a format specification */
#define FLAGS	"-+ #0"

/*
** maximum size of each format specification (such as "%-099.99d")
*/
#define MAX_FORMAT	32


static void addquoted (luaL_Buffer *b, const char *s, size_t len) {
  luaL_addchar(b, '"');
  while (len--) {
    if (*s == '"' || *s == '\\' || *s == '\n') {
      luaL_addchar(b, '\\');
      luaL_addchar(b, *s);
    }
    else if (iscntrl(uchar(*s))) {
      char buff[10];
      if (!isdigit(uchar(*(s+1))))
        l_sprintf(buff, sizeof(buff), "\\%d", (int)uchar(*s));
      else
        l_sprintf(buff, sizeof(buff), "\\%03d", (int)uchar(*s));
      luaL_addstring(b, buff);
    }
    else
      luaL_addchar(b, *s);
    s++;
  }
  luaL_addchar(b, '"');
}


/*
** Ensures the 'buff' string uses a dot as the radix character.
*/
static void checkdp (char *buff, int nb) {
  if (memchr(buff, '.', nb) == NULL) {  /* no dot? */
    char point = lua_getlocaledecpoint();  /* try locale point */
    char *ppoint = (char *)memchr(buff, point, nb);
    if (ppoint) *ppoint = '.';  /* change it to a dot */
  }
}


static void addliteral (lua_State *L, luaL_Buffer *b, int arg) {
  switch (lua_type(L, arg)) {
    case LUA_TSTRING: {
      size_t len;
      const char *s = lua_tolstring(L, arg, &len);
      addquoted(b, s, len);
      break;
    }
    case LUA_TNUMBER: {
      char *buff = luaL_prepbuffsize(b, MAX_ITEM);
      int nb;
      if (!lua_isinteger(L, arg)) {  /* float? */
        lua_Number n = lua_tonumber(L, arg);  /* write as hexa ('%a') */
        nb = lua_number2strx(L, buff, MAX_ITEM, "%" LUA_NUMBER_FRMLEN "a", n);
        checkdp(buff, nb);  /* ensure it uses a dot */
      }
      else {  /* integers */
        lua_Integer n = lua_tointeger(L, arg);
        const char *format = (n == LUA_MININTEGER)  /* corner case? */
                           ? "0x%" LUA_INTEGER_FRMLEN "x"  /* use hexa */
                           : LUA_INTEGER_FMT;  /* else use default format */
        nb = l_sprintf(buff, MAX_ITEM, format, (LUAI_UACINT)n);
      }
      luaL_addsize(b, nb);
      break;
    }
    case LUA_TNIL: case LUA_TBOOLEAN: {
      luaL_tolstring(L, arg, NULL);
      luaL_addvalue(b);
      break;
    }
    default: {
      luaL_argerror(L, arg, "valor n\xC3\xA3o tem a forma literal");
    }
  }
}


static const char *scanformat (lua_State *L, const char *strfrmt, char *form) {
  const char *p = strfrmt;
  while (*p != '\0' && strchr(FLAGS, *p) != NULL) p++;  /* skip flags */
  if ((size_t)(p - strfrmt) >= sizeof(FLAGS)/sizeof(char))
    luaL_error(L, "formato inv\xC3\xA1lido (marcadores repetidos)");
  if (isdigit(uchar(*p))) p++;  /* skip width */
  if (isdigit(uchar(*p))) p++;  /* (2 digits at most) */
  if (*p == '.') {
    p++;
    if (isdigit(uchar(*p))) p++;  /* skip precision */
    if (isdigit(uchar(*p))) p++;  /* (2 digits at most) */
  }
  if (isdigit(uchar(*p)))
    luaL_error(L, "formato inv\xC3\xA1lido (largura ou precis\xC3\xA3o longa demais)");
  *(form++) = '%';
  memcpy(form, strfrmt, ((p - strfrmt) + 1) * sizeof(char));
  form += (p - strfrmt) + 1;
  *form = '\0';
  return p;
}


/*
** add length modifier into formats
*/
static void addlenmod (char *form, const char *lenmod) {
  size_t l = strlen(form);
  size_t lm = strlen(lenmod);
  char spec = form[l - 1];
  strcpy(form + l - 1, lenmod);
  form[l + lm - 1] = spec;
  form[l + lm] = '\0';
}


static int str_format (lua_State *L) {
  int top = lua_gettop(L);
  int arg = 1;
  size_t sfl;
  const char *strfrmt = luaL_checklstring(L, arg, &sfl);
  const char *strfrmt_end = strfrmt+sfl;
  luaL_Buffer b;
  luaL_buffinit(L, &b);
  while (strfrmt < strfrmt_end) {
    if (*strfrmt != L_ESC)
      luaL_addchar(&b, *strfrmt++);
    else if (*++strfrmt == L_ESC)
      luaL_addchar(&b, *strfrmt++);  /* %% */
    else { /* format item */
      char form[MAX_FORMAT];  /* to store the format ('%...') */
      char *buff = luaL_prepbuffsize(&b, MAX_ITEM);  /* to put formatted item */
      int nb = 0;  /* number of bytes in added item */
      if (++arg > top)
        luaL_argerror(L, arg, "sem valor");
      strfrmt = scanformat(L, strfrmt, form);
      switch (*strfrmt++) {
        case 'c': {
          nb = l_sprintf(buff, MAX_ITEM, form, (int)luaL_checkinteger(L, arg));
          break;
        }
        case 'd': case 'i':
        case 'o': case 'u': case 'x': case 'X': {
          lua_Integer n = luaL_checkinteger(L, arg);
          addlenmod(form, LUA_INTEGER_FRMLEN);
          nb = l_sprintf(buff, MAX_ITEM, form, (LUAI_UACINT)n);
          break;
        }
        case 'a': case 'A':
          addlenmod(form, LUA_NUMBER_FRMLEN);
          nb = lua_number2strx(L, buff, MAX_ITEM, form,
                                  luaL_checknumber(L, arg));
          break;
        case 'e': case 'E': case 'f':
        case 'g': case 'G': {
          lua_Number n = luaL_checknumber(L, arg);
          addlenmod(form, LUA_NUMBER_FRMLEN);
          nb = l_sprintf(buff, MAX_ITEM, form, (LUAI_UACNUMBER)n);
          break;
        }
        case 'q': {
          addliteral(L, &b, arg);
          break;
        }
        case 's': {
          size_t l;
          const char *s = luaL_tolstring(L, arg, &l);
          if (form[2] == '\0')  /* no modifiers? */
            luaL_addvalue(&b);  /* keep entire string */
          else {
            luaL_argcheck(L, l == strlen(s), arg, "o colar cont\xC3\xA9m zeros");
            if (!strchr(form, '.') && l >= 100) {
              /* no precision and string is too long to be formatted */
              luaL_addvalue(&b);  /* keep entire string */
            }
            else {  /* format the string into 'buff' */
              nb = l_sprintf(buff, MAX_ITEM, form, s);
              lua_pop(L, 1);  /* remove result from 'luaL_tolstring' */
            }
          }
          break;
        }
        default: {  /* also treat cases 'pnLlh' */
          return luaL_error(L, "op\xC3\xA7\xC3\xA3o '%%%c' inv\xC3\xA1lida para 'formate'",
                               *(strfrmt - 1));
        }
      }
      lua_assert(nb < MAX_ITEM);
      luaL_addsize(&b, nb);
    }
  }
  luaL_pushresult(&b);
  return 1;
}

/* }====================================================== */


/*
** {======================================================
** PACK/UNPACK
** =======================================================
*/


/* value used for padding */
#if !defined(LUAL_PACKPADBYTE)
#define LUAL_PACKPADBYTE		0x00
#endif

/* maximum size for the binary representation of an integer */
#define MAXINTSIZE	16

/* number of bits in a character */
#define NB	CHAR_BIT

/* mask for one character (NB 1's) */
#define MC	((1 << NB) - 1)

/* size of a lua_Integer */
#define SZINT	((int)sizeof(lua_Integer))


/* dummy union to get native endianness */
static const union {
  int dummy;
  char little;  /* true iff machine is little endian */
} nativeendian = {1};


/* dummy structure to get native alignment requirements */
struct cD {
  char c;
  union { double d; void *p; lua_Integer i; lua_Number n; } u;
};

#define MAXALIGN	(offsetof(struct cD, u))


/*
** Union for serializing floats
*/
typedef union Ftypes {
  float f;
  double d;
  lua_Number n;
  char buff[5 * sizeof(lua_Number)];  /* enough for any float type */
} Ftypes;


/*
** information to pack/unpack stuff
*/
typedef struct Header {
  lua_State *L;
  int islittle;
  int maxalign;
} Header;


/*
** options for pack/unpack
*/
typedef enum KOption {
  Kint,		/* signed integers */
  Kuint,	/* unsigned integers */
  Kfloat,	/* floating-point numbers */
  Kchar,	/* fixed-length strings */
  Kstring,	/* strings with prefixed length */
  Kzstr,	/* zero-terminated strings */
  Kpadding,	/* padding */
  Kpaddalign,	/* padding for alignment */
  Knop		/* no-op (configuration or spaces) */
} KOption;


/*
** Read an integer numeral from string 'fmt' or return 'df' if
** there is no numeral
*/
static int digit (int c) { return '0' <= c && c <= '9'; }

static int getnum (const char **fmt, int df) {
  if (!digit(**fmt))  /* no number? */
    return df;  /* return default value */
  else {
    int a = 0;
    do {
      a = a*10 + (*((*fmt)++) - '0');
    } while (digit(**fmt) && a <= ((int)MAXSIZE - 9)/10);
    return a;
  }
}


/*
** Read an integer numeral and raises an error if it is larger
** than the maximum size for integers.
*/
static int getnumlimit (Header *h, const char **fmt, int df) {
  int sz = getnum(fmt, df);
  if (sz > MAXINTSIZE || sz <= 0)
    return luaL_error(h->L, "tamanho inteiro (%d) fora dos limites [1,%d]",
                            sz, MAXINTSIZE);
  return sz;
}


/*
** Initialize Header
*/
static void initheader (lua_State *L, Header *h) {
  h->L = L;
  h->islittle = nativeendian.little;
  h->maxalign = 1;
}


/*
** Read and classify next option. 'size' is filled with option's size.
*/
static KOption getoption (Header *h, const char **fmt, int *size) {
  int opt = *((*fmt)++);
  *size = 0;  /* default */
  switch (opt) {
    case 'b': *size = sizeof(char); return Kint;
    case 'B': *size = sizeof(char); return Kuint;
    case 'h': *size = sizeof(short); return Kint;
    case 'H': *size = sizeof(short); return Kuint;
    case 'l': *size = sizeof(long); return Kint;
    case 'L': *size = sizeof(long); return Kuint;
    case 'j': *size = sizeof(lua_Integer); return Kint;
    case 'J': *size = sizeof(lua_Integer); return Kuint;
    case 'T': *size = sizeof(size_t); return Kuint;
    case 'f': *size = sizeof(float); return Kfloat;
    case 'd': *size = sizeof(double); return Kfloat;
    case 'n': *size = sizeof(lua_Number); return Kfloat;
    case 'i': *size = getnumlimit(h, fmt, sizeof(int)); return Kint;
    case 'I': *size = getnumlimit(h, fmt, sizeof(int)); return Kuint;
    case 's': *size = getnumlimit(h, fmt, sizeof(size_t)); return Kstring;
    case 'c':
      *size = getnum(fmt, -1);
      if (*size == -1)
        luaL_error(h->L, "falta o tamanho para a op\xC3\xA7\xC3\xA3o de formato 'c'");
      return Kchar;
    case 'z': return Kzstr;
    case 'x': *size = 1; return Kpadding;
    case 'X': return Kpaddalign;
    case ' ': break;
    case '<': h->islittle = 1; break;
    case '>': h->islittle = 0; break;
    case '=': h->islittle = nativeendian.little; break;
    case '!': h->maxalign = getnumlimit(h, fmt, MAXALIGN); break;
    default: luaL_error(h->L, "op\xC3\xA7\xC3\xA3o de formato inv\xC3\xA1lida '%c'", opt);
  }
  return Knop;
}


/*
** Read, classify, and fill other details about the next option.
** 'psize' is filled with option's size, 'notoalign' with its
** alignment requirements.
** Local variable 'size' gets the size to be aligned. (Kpadal option
** always gets its full alignment, other options are limited by
** the maximum alignment ('maxalign'). Kchar option needs no alignment
** despite its size.
*/
static KOption getdetails (Header *h, size_t totalsize,
                           const char **fmt, int *psize, int *ntoalign) {
  KOption opt = getoption(h, fmt, psize);
  int align = *psize;  /* usually, alignment follows size */
  if (opt == Kpaddalign) {  /* 'X' gets alignment from following option */
    if (**fmt == '\0' || getoption(h, fmt, &align) == Kchar || align == 0)
      luaL_argerror(h->L, 1,
                    "op\xC3\xA7\xC3\xA3o seguinte inv\xC3\xA1lida para a op\xC3\xA7\xC3\xA3o 'X'");
  }
  if (align <= 1 || opt == Kchar)  /* need no alignment? */
    *ntoalign = 0;
  else {
    if (align > h->maxalign)  /* enforce maximum alignment */
      align = h->maxalign;
    if ((align & (align - 1)) != 0)  /* is 'align' not a power of 2? */
      luaL_argerror(h->L, 1, "o formato solicita alinhamento que n\xC3\xA3o \xC3\xA9 pot\xC3\xAAncia de 2");
    *ntoalign = (align - (int)(totalsize & (align - 1))) & (align - 1);
  }
  return opt;
}


/*
** Pack integer 'n' with 'size' bytes and 'islittle' endianness.
** The final 'if' handles the case when 'size' is larger than
** the size of a Lua integer, correcting the extra sign-extension
** bytes if necessary (by default they would be zeros).
*/
static void packint (luaL_Buffer *b, lua_Unsigned n,
                     int islittle, int size, int neg) {
  char *buff = luaL_prepbuffsize(b, size);
  int i;
  buff[islittle ? 0 : size - 1] = (char)(n & MC);  /* first byte */
  for (i = 1; i < size; i++) {
    n >>= NB;
    buff[islittle ? i : size - 1 - i] = (char)(n & MC);
  }
  if (neg && size > SZINT) {  /* negative number need sign extension? */
    for (i = SZINT; i < size; i++)  /* correct extra bytes */
      buff[islittle ? i : size - 1 - i] = (char)MC;
  }
  luaL_addsize(b, size);  /* add result to buffer */
}


/*
** Copy 'size' bytes from 'src' to 'dest', correcting endianness if
** given 'islittle' is different from native endianness.
*/
static void copywithendian (volatile char *dest, volatile const char *src,
                            int size, int islittle) {
  if (islittle == nativeendian.little) {
    while (size-- != 0)
      *(dest++) = *(src++);
  }
  else {
    dest += size - 1;
    while (size-- != 0)
      *(dest--) = *(src++);
  }
}


static int str_pack (lua_State *L) {
  luaL_Buffer b;
  Header h;
  const char *fmt = luaL_checkstring(L, 1);  /* format string */
  int arg = 1;  /* current argument to pack */
  size_t totalsize = 0;  /* accumulate total size of result */
  initheader(L, &h);
  lua_pushnil(L);  /* mark to separate arguments from string buffer */
  luaL_buffinit(L, &b);
  while (*fmt != '\0') {
    int size, ntoalign;
    KOption opt = getdetails(&h, totalsize, &fmt, &size, &ntoalign);
    totalsize += ntoalign + size;
    while (ntoalign-- > 0)
     luaL_addchar(&b, LUAL_PACKPADBYTE);  /* fill alignment */
    arg++;
    switch (opt) {
      case Kint: {  /* signed integers */
        lua_Integer n = luaL_checkinteger(L, arg);
        if (size < SZINT) {  /* need overflow check? */
          lua_Integer lim = (lua_Integer)1 << ((size * NB) - 1);
          luaL_argcheck(L, -lim <= n && n < lim, arg, "estouro de inteiro");
        }
        packint(&b, (lua_Unsigned)n, h.islittle, size, (n < 0));
        break;
      }
      case Kuint: {  /* unsigned integers */
        lua_Integer n = luaL_checkinteger(L, arg);
        if (size < SZINT)  /* need overflow check? */
          luaL_argcheck(L, (lua_Unsigned)n < ((lua_Unsigned)1 << (size * NB)),
                           arg, "estouro de inteiro sem sinal");
        packint(&b, (lua_Unsigned)n, h.islittle, size, 0);
        break;
      }
      case Kfloat: {  /* floating-point options */
        volatile Ftypes u;
        char *buff = luaL_prepbuffsize(&b, size);
        lua_Number n = luaL_checknumber(L, arg);  /* get argument */
        if (size == sizeof(u.f)) u.f = (float)n;  /* copy it into 'u' */
        else if (size == sizeof(u.d)) u.d = (double)n;
        else u.n = n;
        /* move 'u' to final result, correcting endianness if needed */
        copywithendian(buff, u.buff, size, h.islittle);
        luaL_addsize(&b, size);
        break;
      }
      case Kchar: {  /* fixed-size string */
        size_t len;
        const char *s = luaL_checklstring(L, arg, &len);
        luaL_argcheck(L, len <= (size_t)size, arg,
                         "colar maior que o tamanho fornecido");
        luaL_addlstring(&b, s, len);  /* add string */
        while (len++ < (size_t)size)  /* pad extra space */
          luaL_addchar(&b, LUAL_PACKPADBYTE);
        break;
      }
      case Kstring: {  /* strings with length count */
        size_t len;
        const char *s = luaL_checklstring(L, arg, &len);
        luaL_argcheck(L, size >= (int)sizeof(size_t) ||
                         len < ((size_t)1 << (size * NB)),
                         arg, "o tamanho do colar n\xC3\xA3o cabe no tamanho fornecido");
        packint(&b, (lua_Unsigned)len, h.islittle, size, 0);  /* pack length */
        luaL_addlstring(&b, s, len);
        totalsize += len;
        break;
      }
      case Kzstr: {  /* zero-terminated string */
        size_t len;
        const char *s = luaL_checklstring(L, arg, &len);
        luaL_argcheck(L, strlen(s) == len, arg, "o colar cont\xC3\xA9m zeros");
        luaL_addlstring(&b, s, len);
        luaL_addchar(&b, '\0');  /* add zero at the end */
        totalsize += len + 1;
        break;
      }
      case Kpadding: luaL_addchar(&b, LUAL_PACKPADBYTE);  /* FALLTHROUGH */
      case Kpaddalign: case Knop:
        arg--;  /* undo increment */
        break;
    }
  }
  luaL_pushresult(&b);
  return 1;
}


static int str_packsize (lua_State *L) {
  Header h;
  const char *fmt = luaL_checkstring(L, 1);  /* format string */
  size_t totalsize = 0;  /* accumulate total size of result */
  initheader(L, &h);
  while (*fmt != '\0') {
    int size, ntoalign;
    KOption opt = getdetails(&h, totalsize, &fmt, &size, &ntoalign);
    size += ntoalign;  /* total space used by option */
    luaL_argcheck(L, totalsize <= MAXSIZE - size, 1,
                     "resultado do formato grande demais");
    totalsize += size;
    switch (opt) {
      case Kstring:  /* strings with length count */
      case Kzstr:    /* zero-terminated string */
        luaL_argerror(L, 1, "formato de tamanho vari\xC3\xA1vel");
        /* call never return, but to avoid warnings: *//* FALLTHROUGH */
      default:  break;
    }
  }
  lua_pushinteger(L, (lua_Integer)totalsize);
  return 1;
}


/*
** Unpack an integer with 'size' bytes and 'islittle' endianness.
** If size is smaller than the size of a Lua integer and integer
** is signed, must do sign extension (propagating the sign to the
** higher bits); if size is larger than the size of a Lua integer,
** it must check the unread bytes to see whether they do not cause an
** overflow.
*/
static lua_Integer unpackint (lua_State *L, const char *str,
                              int islittle, int size, int issigned) {
  lua_Unsigned res = 0;
  int i;
  int limit = (size  <= SZINT) ? size : SZINT;
  for (i = limit - 1; i >= 0; i--) {
    res <<= NB;
    res |= (lua_Unsigned)(unsigned char)str[islittle ? i : size - 1 - i];
  }
  if (size < SZINT) {  /* real size smaller than lua_Integer? */
    if (issigned) {  /* needs sign extension? */
      lua_Unsigned mask = (lua_Unsigned)1 << (size*NB - 1);
      res = ((res ^ mask) - mask);  /* do sign extension */
    }
  }
  else if (size > SZINT) {  /* must check unread bytes */
    int mask = (!issigned || (lua_Integer)res >= 0) ? 0 : MC;
    for (i = limit; i < size; i++) {
      if ((unsigned char)str[islittle ? i : size - 1 - i] != mask)
        luaL_error(L, "inteiro de %d bytes n\xC3\xA3o cabe em um inteiro Santaf\xC3\xA9", size);
    }
  }
  return (lua_Integer)res;
}


static int str_unpack (lua_State *L) {
  Header h;
  const char *fmt = luaL_checkstring(L, 1);
  size_t ld;
  const char *data = luaL_checklstring(L, 2, &ld);
  size_t pos = (size_t)posrelat(luaL_optinteger(L, 3, 1), ld) - 1;
  int n = 0;  /* number of results */
  luaL_argcheck(L, pos <= ld, 3, "posi\xC3\xA7\xC3\xA3o inicial fora do colar");
  initheader(L, &h);
  while (*fmt != '\0') {
    int size, ntoalign;
    KOption opt = getdetails(&h, pos, &fmt, &size, &ntoalign);
    if ((size_t)ntoalign + size > ~pos || pos + ntoalign + size > ld)
      luaL_argerror(L, 2, "dados do colar insuficientes");
    pos += ntoalign;  /* skip alignment */
    /* stack space for item + next position */
    luaL_checkstack(L, 2, "muitos resultados");
    n++;
    switch (opt) {
      case Kint:
      case Kuint: {
        lua_Integer res = unpackint(L, data + pos, h.islittle, size,
                                       (opt == Kint));
        lua_pushinteger(L, res);
        break;
      }
      case Kfloat: {
        volatile Ftypes u;
        lua_Number num;
        copywithendian(u.buff, data + pos, size, h.islittle);
        if (size == sizeof(u.f)) num = (lua_Number)u.f;
        else if (size == sizeof(u.d)) num = (lua_Number)u.d;
        else num = u.n;
        lua_pushnumber(L, num);
        break;
      }
      case Kchar: {
        lua_pushlstring(L, data + pos, size);
        break;
      }
      case Kstring: {
        size_t len = (size_t)unpackint(L, data + pos, h.islittle, size, 0);
        luaL_argcheck(L, pos + len + size <= ld, 2, "dados do colar insuficientes");
        lua_pushlstring(L, data + pos + size, len);
        pos += len;  /* skip string */
        break;
      }
      case Kzstr: {
        size_t len = (int)strlen(data + pos);
        lua_pushlstring(L, data + pos, len);
        pos += len + 1;  /* skip string plus final '\0' */
        break;
      }
      case Kpaddalign: case Kpadding: case Knop:
        n--;  /* undo increment */
        break;
    }
    pos += size;
  }
  lua_pushinteger(L, pos + 1);  /* next position */
  return n + 1;
}


/* --- IMPLEMENTAÇÃO RAFAEL --- */
/* --- FUNÇÕES EXTRAS DO SANTAFÉ (Base64, Hex, Trim, Join) --- */

/* 1. APARE (Trim) - Remove espaços do começo e fim */
static int str_trim (lua_State *L) {
  size_t l;
  const char *s = luaL_checklstring(L, 1, &l);
  while (l > 0 && isspace((unsigned char)*s)) { /* Começo */
    s++; l--;
  }
  while (l > 0 && isspace((unsigned char)s[l-1])) { /* Fim */
    l--;
  }
  lua_pushlstring(L, s, l);
  return 1;
}

/* 2. HEX / DECHEX (Converte colar para hexadecimal e vice-versa) */
static int str_tohex (lua_State *L) {
  size_t l;
  const char *s = luaL_checklstring(L, 1, &l);
  luaL_Buffer b;
  luaL_buffinit(L, &b);
  size_t i;
  for (i = 0; i < l; i++) {
    char buff[4];
    sprintf(buff, "%02X", (unsigned char)s[i]);
    luaL_addstring(&b, buff);
  }
  luaL_pushresult(&b);
  return 1;
}

static int str_fromhex (lua_State *L) {
  size_t l;
  const char *s = luaL_checklstring(L, 1, &l);
  if (l % 2 != 0) return luaL_error(L, "colar hexadecimal inv\xC3\xA1lido (tamanho \xC3\xADmpar)");
  luaL_Buffer b;
  luaL_buffinit(L, &b);
  size_t i;
  for (i = 0; i < l; i += 2) {
    unsigned int x;
    if (sscanf(s + i, "%2x", &x) != 1)
      return luaL_error(L, "caractere hexadecimal inv\xC3\xA1lido");
    luaL_addchar(&b, (char)x);
  }
  luaL_pushresult(&b);
  return 1;
}

/* 3. BASE64 / DECBASE64 */
static const char b64[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

static int str_base64 (lua_State *L) {
  size_t l;
  const char *s = luaL_checklstring(L, 1, &l);
  luaL_Buffer b;
  luaL_buffinit(L, &b);
  size_t i;
  for (i = 0; i < l; i += 3) {
    unsigned int v = 0;
    int j;
    for (j = 0; j < 3; j++) {
      v <<= 8;
      if (i + j < l) v |= (unsigned char)s[i + j];
    }
    char buff[5];
    buff[0] = b64[(v >> 18) & 0x3F];
    buff[1] = b64[(v >> 12) & 0x3F];
    buff[2] = (i + 1 < l) ? b64[(v >> 6) & 0x3F] : '=';
    buff[3] = (i + 2 < l) ? b64[v & 0x3F] : '=';
    buff[4] = '\0';
    luaL_addstring(&b, buff);
  }
  luaL_pushresult(&b);
  return 1;
}

static int str_unbase64 (lua_State *L) {
  size_t l;
  const char *s = luaL_checklstring(L, 1, &l);
  luaL_Buffer b;
  luaL_buffinit(L, &b);
  int val[256];
  int i;
  for (i = 0; i < 256; i++) val[i] = -1;
  for (i = 0; i < 64; i++) val[(unsigned char)b64[i]] = i;

  unsigned int v = 0;
  int bits = 0;
  for (i = 0; i < (int)l; i++) {
    int c = (unsigned char)s[i];
    if (c == '=') break;
    if (isspace(c)) continue; /* Ignora espaços */
    if (val[c] == -1) return luaL_error(L, "caractere base64 inv\xC3\xA1lido");
    v = (v << 6) | val[c];
    bits += 6;
    if (bits >= 8) {
      bits -= 8;
      luaL_addchar(&b, (char)((v >> bits) & 0xFF));
    }
  }
  luaL_pushresult(&b);
  return 1;
}

/* 4. JUNTE (Join) - Concatena argumentos com um separador */
/* Uso atual: colar.junte(" - ", "a", "b", "c") */
static int str_join (lua_State *L) {
  int n = lua_gettop(L);
  if (n < 2) return luaL_error(L, "esperados um separador e pelo menos um colar");
  const char *sep = luaL_checkstring(L, 1);
  luaL_Buffer b;
  luaL_buffinit(L, &b);
  int i;
  for (i = 2; i <= n; i++) {
    luaL_addvalue(&b); /* Adiciona o argumento à pilha */
    if (i < n) luaL_addstring(&b, sep);
  }
  luaL_pushresult(&b);
  return 1;
}


/* --- FUNÇÕES ZLIB (COMPACTAR / DESCOMPACTAR) --- */

/* COMPACTAR: colar original -> binário Zlib */
static int str_compress_raw (lua_State *L) {
    size_t l;
    const char *s = luaL_checklstring(L, 1, &l);

    /* Zlib calcula o tamanho máximo que o dado comprimido pode ter */
    uLongf destLen = compressBound(l);

    unsigned char *dest = (unsigned char *)malloc(destLen);
    if (dest == NULL) return luaL_error(L, "mem\xC3\xB3ria insuficiente");

    int res = compress(dest, &destLen, (const unsigned char *)s, l);

    if (res != Z_OK) {
        free(dest);
        return luaL_error(L, "erro interno na compacta\xC3\xA7\xC3\xA3o");
    }

    lua_pushlstring(L, (char *)dest, destLen);
    free(dest);
    return 1;
}

/* DESCOMPACTAR: binário Zlib -> colar original */
static int str_decompress_raw (lua_State *L) {
    size_t l;
    const char *s = luaL_checklstring(L, 1, &l);

    /* Chute inicial: 4x o tamanho comprimido */
    uLongf destLen = l * 4;
    if (destLen < 1024) destLen = 1024;

    unsigned char *dest = (unsigned char *)malloc(destLen);
    if (dest == NULL) return luaL_error(L, "mem\xC3\xB3ria insuficiente");

    /* Loop para tentar descompactar. Se o buffer for pequeno, dobramos e tentamos de novo */
    int res = uncompress(dest, &destLen, (const unsigned char *)s, l);

    while (res == Z_BUF_ERROR) {
        free(dest);
        destLen *= 2; /* Dobra o tamanho */
        dest = (unsigned char *)malloc(destLen);
        if (dest == NULL) return luaL_error(L, "mem\xC3\xB3ria insuficiente (arquivo muito grande)");

        res = uncompress(dest, &destLen, (const unsigned char *)s, l);
    }

    if (res != Z_OK) {
        free(dest);
        return luaL_error(L, "dados corrompidos ou inv\xC3\xA1lidos (erro zlib)");
    }

    lua_pushlstring(L, (char *)dest, destLen);
    free(dest);
    return 1;
}

/* Função para calcular CRC32 usando a Zlib embutida */
static int str_crc32 (lua_State *L) {
  size_t l;
  /* Pega o colar/binário da pilha */
  const char *s = luaL_checklstring(L, 1, &l);

  /* Chama a função nativa da Zlib */
  /* O primeiro argumento '0L' inicia o cálculo do zero */
  unsigned long res = crc32(0L, (const unsigned char*)s, l);

  /* Retorna o número inteiro para o Santafé */
  lua_pushinteger(L, (lua_Integer)res);
  return 1;
}

/* Busca variável na pilha da função que chamou (Locais) ou Global */
static void push_variable(lua_State *L, const char *name) {
    lua_Debug ar;
    int i;
    const char *local_name;

    /* 1. Tenta achar nas LOCAIS da função anterior (Level 1) */
    if (lua_getstack(L, 1, &ar)) {
        i = 1;
        while ((local_name = lua_getlocal(L, &ar, i++)) != NULL) {
            if (strcmp(local_name, name) == 0) {
                return; /* Achou! Valor está no topo da pilha */
            }
            lua_pop(L, 1); /* Não é esse, remove e continua */
        }
    }

    /* 2. Se não achou, tenta na GLOBAL */
    lua_getglobal(L, name);
}
/*
** gabarito literal estilo JS simples:
**  - Usa marcador UTF-8 '®' (0xC2 0xAE) dentro da string:
**      ®nome      -> usa variável (local ou global) 'nome'
**      ®{expr}    -> avalia expressão como "retorne expr"
**  - ESCAPE:
**      \®         -> gera ® literal
**      \®{...}    -> gera ®{...} literal (sem interpolar)
*/

/* ** Função __gabarito (Processa ® e Ⓡ)
** Suporta: ®var, Ⓡvar, ®{...}, Ⓡ{...}
*/
static int str_gabarito (lua_State *L) {
  size_t tam;
  const char *src = luaL_checklstring(L, 1, &tam);
  luaL_Buffer b;
  size_t i = 0;

  luaL_buffinit(L, &b);

  while (i < tam) {
    unsigned char c = (unsigned char)src[i];

    /* 1. VERIFICA ESCAPE (\® ou \Ⓡ) */
    if (c == '\\' && i + 1 < tam) {
        /* Escape de ® (2 bytes: C2 AE) */
        if (i + 2 < tam && (unsigned char)src[i+1] == 0xC2 && (unsigned char)src[i+2] == 0xAE) {
            luaL_addstring(&b, "\xC2\xAE");
            i += 3; continue;
        }
        /* Escape de Ⓡ (3 bytes: E2 93 87) */
        if (i + 3 < tam && (unsigned char)src[i+1] == 0xE2 && (unsigned char)src[i+2] == 0x93 && (unsigned char)src[i+3] == 0x87) {
            luaL_addstring(&b, "\xE2\x93\x87");
            i += 4; continue;
        }
    }

    /* 2. DETECTA O SÍMBOLO DE INTERPOLAÇÃO */
    int tam_simbolo = 0;

    /* Verifica ® (C2 AE) */
    if (i + 1 < tam && c == 0xC2 && (unsigned char)src[i+1] == 0xAE) {
        tam_simbolo = 2;
    }
    /* Verifica Ⓡ (E2 93 87) */
    else if (i + 2 < tam && c == 0xE2 && (unsigned char)src[i+1] == 0x93 && (unsigned char)src[i+2] == 0x87) {
        tam_simbolo = 3;
    }

    /* Se encontrou algum dos dois símbolos... */
    if (tam_simbolo > 0) {
      /* O próximo caractere útil está em i + tam_simbolo */
      unsigned char c_prox = (i + tam_simbolo < tam) ? (unsigned char)src[i + tam_simbolo] : 0;

      /* CASO A: {expressão} */
      if (c_prox == '{') {
        size_t inicio = i + tam_simbolo + 1; /* Pula Símbolo + { */
        size_t j = inicio;
        int profundidade = 1;

        while (j < tam && profundidade > 0) {
          if (src[j] == '{') profundidade++;
          else if (src[j] == '}') profundidade--;
          j++;
        }

        if (profundidade != 0) return luaL_error(L, "gabarito n\xC3\xA3o finalizado (falta '}')");

        /* Compila e executa */
        lua_pushliteral(L, "retorne ");
        lua_pushlstring(L, src + inicio, (j - 1) - inicio);
        lua_concat(L, 2);

        if (luaL_loadbuffer(L, lua_tostring(L, -1), lua_rawlen(L, -1), "=(gabarito)") != LUA_OK) {
            return lua_error(L);
        }
        lua_remove(L, -2);

        /* Por padrão, um chunk carregado com luaL_loadbuffer só enxerga
           GLOBAIS (seu upvalue _ENV aponta pra tabela global) — variáveis
           locais de quem escreveu o ®{...} ficariam invisíveis. Damos a ele
           um _ENV próprio: uma tabela com as locais do chamador, e
           metatabela __índice apontando pra tabela global de verdade (então
           tudo que não for local continua resolvendo como global igual
           antes). */
        {
            int func_idx = lua_gettop(L); /* índice da função recém-carregada */

            lua_newtable(L);              /* ambiente customizado (E) */
            lua_createtable(L, 0, 1);     /* metatabela de E */
            lua_pushglobaltable(L);
            lua_setfield(L, -2, LUA_MM_INDICE);
            lua_setmetatable(L, -2);      /* pilha: [..., func, E] */

            {
                lua_Debug ar;
                if (lua_getstack(L, 1, &ar)) { /* nível 1 = quem chamou __gabarito */
                    int idx = 1;
                    const char *local_name;
                    while ((local_name = lua_getlocal(L, &ar, idx++)) != NULL) {
                        /* pilha: [..., func, E, valor_local]; grava em E e consome */
                        lua_setfield(L, -2, local_name);
                    }
                }
            }

            lua_setupvalue(L, func_idx, 1); /* _ENV da função = E; consome E */
        }

        lua_call(L, 0, 1);

        lua_getglobal(L, "paraColar");
        lua_pushvalue(L, -2);
        lua_call(L, 1, 1);
        luaL_addvalue(&b);
        lua_pop(L, 1);

        i = j;
        continue;
      }

      /* CASO B: variavel (sem chaves) */
      else if (isalpha(c_prox) || c_prox == '_') {
        size_t inicio = i + tam_simbolo;
        size_t j = inicio;
        while (j < tam && (isalnum((unsigned char)src[j]) || src[j] == '_')) {
            j++;
        }

        char *nome_var = malloc((j - inicio) + 1);
        memcpy(nome_var, src + inicio, j - inicio);
        nome_var[j - inicio] = '\0';

        /* Função auxiliar que criamos antes para buscar local/global */
        push_variable(L, nome_var);
        free(nome_var);

        if (!lua_isnil(L, -1)) {
            lua_getglobal(L, "paraColar");
            lua_pushvalue(L, -2);
            lua_call(L, 1, 1);
            luaL_addvalue(&b);
            /* pilha aqui: só sobra o valor 'V' empurrado por push_variable
               (paraColar, a cópia e o resultado do paraColar já foram
               consumidos por lua_call/luaL_addvalue); então falta remover
               só ESSE valor, não dois. lua_pop(L, 2) estourava um nível a
               mais da pilha do luaL_Buffer a cada ®var interpolado -- é
               esse acúmulo que gerava o estouro de pilha em gabaritos com
               várias interpolações. */
            lua_pop(L, 1);
        } else {
            lua_pop(L, 1);
        }

        i = j;
        continue;
      }

      /* Se não for { nem letra, trata como símbolo normal (cai no addchar abaixo) */
      /* Adicionar os bytes do símbolo manualmente para não quebrar o loop */
    }

    /* Caractere normal (ou parte de um símbolo ignorado) */
    luaL_addchar(&b, (char)c);
    i++;
  }

  luaL_pushresult(&b);
  return 1;
}


/* }====================================================== */


static const luaL_Reg strlib[] = {
  /* Novas Funções do Santafé */
  {"apare", str_trim},            /* Trim */
  {"junte", str_join},            /* Join */
  {"hex", str_tohex},             /* String -> Hex */
  {"decHex", str_fromhex},        /* Hex -> String */
  {"base64", str_base64},         /* String -> Base64 */
  {"decBase64", str_unbase64},    /* Base64 -> String */
  {"compacte", str_compress_raw}, /* RAW -> ZLIB */
  {"descompacte", str_decompress_raw}, /* ZLIB -> RAW */
  {"crc32", str_crc32},             /* crc32 -- calcular PNG */

  /* Novas Funções do Santafé */
  {"byte", str_byte},              /* byte (código numérico) */
  {"taco", str_byte},              /* apelido de byte */
  {"caractere", str_char},        /* char -> caractere */
  {"bin\xC3\xA1rio", str_dump},   /* dump -> binário */
  {"procure", str_find},          /* find -> procure */
  {"formate", str_format},       /* format -> formatar */
  {"capture", gmatch}, /* gmatch -> combinações (iterador) */
  {"troque", str_gsub},       /* gsub -> substituir */
  {"tamanho", str_len},           /* len -> tamanho */
  {"min\xC3\xBAscula", str_lower}, /* lower -> minúscula */
  {"separe", str_match},        /* match -> separar */
  {"empacote", str_pack},        /* pack -> empacotar */
  {"porte", str_packsize},       /* packsize -> porte */
  {"replique", str_rep},         /* rep -> replique (repita é palavra reservada) */
  {"inverta", str_reverse},      /* reverse -> inverta */
  {"corte", str_sub},                  /* sub -> corte (1,-1) */
  {"desempacote", str_unpack},   /* unpack -> desempacote */
  {"mai\xC3\xBAscula", str_upper}, /* upper -> maiúscula */
  {NULL, NULL}
};

static void createmetatable (lua_State *L) {
  lua_createtable(L, 0, 1);  /* table to be metatable for strings */
  lua_pushliteral(L, "");  /* dummy string */
  lua_pushvalue(L, -2);  /* copy table */
  lua_setmetatable(L, -2);  /* set table as metatable for strings */
  lua_pop(L, 1);  /* pop dummy string */
  lua_pushvalue(L, -2);  /* get string library */
  lua_setfield(L, -2, LUA_MM_INDICE);  /* metatabela.__índice = colar */
  lua_pop(L, 1);  /* pop metatable */
}


/*
** Open string library
*/
LUAMOD_API int luaopen_string (lua_State *L) {
  luaL_newlib(L, strlib);
  createmetatable(L);
  /* função global usada pelo lexer para gabaritos: `...` -> __gabarito "..." */
  lua_pushcfunction(L, str_gabarito);
  lua_setglobal(L, "__gabarito");
  return 1;
}
