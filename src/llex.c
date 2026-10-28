/*
** $Id: llex.c,v 2.96.1.1 2017/04/19 17:20:42 roberto Exp $
** Lexical Analyzer
** See Copyright Notice in lua.h
*/

#define llex_c
#define LUA_CORE

#include "lprefix.h"


#include <locale.h>
#include <string.h>

#include "lua.h"
#include "lauxlib.h"

#include "lctype.h"
#include "ldebug.h"
#include "ldo.h"
#include "lgc.h"
#include "llex.h"
#include "lobject.h"
#include "lparser.h"
#include "lstate.h"
#include "lstring.h"
#include "ltable.h"
#include "lunicode.h"
#include "lzio.h"



#define next(ls) ((ls)->offset += ((ls)->current != EOZ), \
                  (ls)->current = zgetc((ls)->z))



#define currIsNewline(ls)	(ls->current == '\n' || ls->current == '\r')



static const char *const luaX_tokens [] = {
    "e", "pare", ("in\xC3\xAD" "cio"), "sen\xC3\xA3o", "sen\xC3\xA3ose",
    "fim", "falso", "para", "fun\xC3\xA7\xC3\xA3o", "v\xC3\xA1para", "se",
    "em", "local", "nulo", "n\xC3\xA3o", "ou", "repita",
    "retorne", "ent\xC3\xA3o", "verdadeiro", "at\xC3\xA9", "enquanto",
    "//", "..", "...", "==", ">=", "<=", "~=",
    "<<", ">>", "::", "<fim do arquivo>",
    "<n\xC3\xBAmero>", "<inteiro>", "<nome>", "<colar>"
};


#define save_and_next(ls) (save(ls, ls->current), next(ls))


static l_noret lexerror (LexState *ls, const char *msg, int token);


static void save (LexState *ls, int c) {
  Mbuffer *b = ls->buff;
  if (luaZ_bufflen(b) + 1 > luaZ_sizebuffer(b)) {
    size_t newsize;
    if (luaZ_sizebuffer(b) >= MAX_SIZE/2)
      lexerror(ls, "elemento l\xC3\xA9xico muito longo", 0);
    newsize = luaZ_sizebuffer(b) * 2;
    luaZ_resizebuffer(ls->L, b, newsize);
  }
  b->buffer[luaZ_bufflen(b)++] = cast(char, c);
}


void luaX_init (lua_State *L) {
  int i;
  TString *e = luaS_newliteral(L, SANTAFE_AMBIENTE);  /* nome do ambiente */
  luaC_fix(L, obj2gco(e));  /* never collect this name */
  for (i=0; i<NUM_RESERVED; i++) {
    TString *ts = luaS_new(L, luaX_tokens[i]);
    luaC_fix(L, obj2gco(ts));  /* reserved words are never collected */
    ts->extra = cast_byte(i+1);  /* reserved word */
  }
}


const char *luaX_token2str (LexState *ls, int token) {
  if (token < FIRST_RESERVED) {  /* single-byte symbols? */
    lua_assert(token == cast_uchar(token));
    return luaO_pushfstring(ls->L, "'%c'", token);
  }
  else {
    const char *s = luaX_tokens[token - FIRST_RESERVED];
    if (token < TK_EOS)  /* fixed format (symbols and reserved words)? */
      return luaO_pushfstring(ls->L, "'%s'", s);
    else  /* names, strings, and numerals */
      return s;
  }
}


static const char *txtToken (LexState *ls, int token) {
  switch (token) {
    case TK_NAME: case TK_STRING:
    case TK_FLT: case TK_INT:
      save(ls, '\0');
      return luaO_pushfstring(ls->L, "'%s'", luaZ_buffer(ls->buff));
    default:
      return luaX_token2str(ls, token);
  }
}


static l_noret lexerror (LexState *ls, const char *msg, int token) {
  lua_Diagnostic *diagnostic = ls->z->diagnostic;
  if (diagnostic) {
    diagnostic->start = ls->scanning ? ls->tokenstart : ls->t.start;
    diagnostic->end = ls->scanning ? ls->offset : ls->t.end;
    diagnostic->hasrange = 1;
  }
  msg = luaG_addinfo(ls->L, msg, ls->source, ls->linenumber);
  if (token)
    luaO_pushfstring(ls->L, "%s pr\xC3\xB3ximo %s", msg, txtToken(ls, token));
  luaD_throw(ls->L, LUA_ERRSYNTAX);
}


l_noret luaX_syntaxerror (LexState *ls, const char *msg) {
  lexerror(ls, msg, ls->t.token);
}


/*
** creates a new string and anchors it in scanner's table so that
** it will not be collected until the end of the compilation
** (by that time it should be anchored somewhere)
*/
TString *luaX_newstring (LexState *ls, const char *str, size_t l) {
  lua_State *L = ls->L;
  TValue *o;  /* entry for 'str' */
  TString *ts = luaS_newlstr(L, str, l);  /* create new string */
  setsvalue2s(L, L->top++, ts);  /* temporarily anchor it in stack */
  o = luaH_set(L, ls->h, L->top - 1);
  if (ttisnil(o)) {  /* not in use yet? */
    /* boolean value does not need GC barrier;
       table has no metatable, so it does not need to invalidate cache */
    setbvalue(o, 1);  /* t[string] = true */
    luaC_checkGC(L);
  }
  else {  /* string already present */
    ts = tsvalue(keyfromval(o));  /* re-use value previously stored */
  }
  L->top--;  /* remove string from stack */
  return ts;
}


/*
** increment line number and skips newline sequence (any of
** \n, \r, \n\r, or \r\n)
*/
static void inclinenumber (LexState *ls) {
  int old = ls->current;
  lua_assert(currIsNewline(ls));
  next(ls);  /* skip '\n' or '\r' */
  if (currIsNewline(ls) && ls->current != old)
    next(ls);  /* skip '\n\r' or '\r\n' */
  if (++ls->linenumber >= MAX_INT)
    lexerror(ls, "trecho tem muitas linhas", 0);
}


void luaX_setinput (lua_State *L, LexState *ls, ZIO *z, TString *source,
                    int firstchar) {
  ls->t.token = 0;
  ls->L = L;
  ls->current = firstchar;
  ls->offset = ls->tokenstart = 0;
  ls->t.start = ls->t.end = 0;
  ls->scanning = 0;
  ls->lookahead.token = TK_EOS;  /* no look-ahead token */
  ls->z = z;
  ls->fs = NULL;
  ls->linenumber = 1;
  ls->lastline = 1;
  ls->source = source;
  ls->envn = luaS_newliteral(L, SANTAFE_AMBIENTE);  /* nome do ambiente */
  luaZ_resizebuffer(ls->L, ls->buff, LUA_MINBUFFER);  /* initialize buffer */
  /* gabarito literal */
  ls->tem_gabarito = 0;
}



/*
** =======================================================
** LEXICAL ANALYZER
** =======================================================
*/


static int check_next1 (LexState *ls, int c) {
  if (ls->current == c) {
    next(ls);
    return 1;
  }
  else return 0;
}


/*
** Check whether current char is in set 'set' (with two chars) and
** saves it
*/
static int check_next2 (LexState *ls, const char *set) {
  lua_assert(set[2] == '\0');
  if (ls->current == set[0] || ls->current == set[1]) {
    save_and_next(ls);
    return 1;
  }
  else return 0;
}


/* LUA_NUMBER */
/*
** this function is quite liberal in what it accepts, as 'luaO_str2num'
** will reject ill-formed numerals.
*/
static int read_numeral (LexState *ls, SemInfo *seminfo) {
  TValue obj;
  const char *expo = "Ee";
  int first = ls->current;
  lua_assert(lisdigit(ls->current));
  save_and_next(ls);
  if (first == '0' && check_next2(ls, "xX"))  /* hexadecimal? */
    expo = "Pp";
  for (;;) {
    if (check_next2(ls, expo))  /* exponent part? */
      check_next2(ls, "-+");  /* optional exponent sign */
    if (lisxdigit(ls->current))
      save_and_next(ls);
    else if (ls->current == '.')
      save_and_next(ls);
    else break;
  }
  save(ls, '\0');
  if (luaO_str2num(luaZ_buffer(ls->buff), &obj) == 0)  /* format error? */
    lexerror(ls, "n\xC3\xBAmero malformado", TK_FLT);
  if (ttisinteger(&obj)) {
    seminfo->i = ivalue(&obj);
    return TK_INT;
  }
  else {
    lua_assert(ttisfloat(&obj));
    seminfo->r = fltvalue(&obj);
    return TK_FLT;
  }
}


/*
** reads a sequence '[=*[' or ']=*]', leaving the last bracket.
** If sequence is well formed, return its number of '='s + 2; otherwise,
** return 1 if there is no '='s or 0 otherwise (an unfinished '[==...').
*/
static size_t skip_sep (LexState *ls) {
  size_t count = 0;
  int s = ls->current;
  lua_assert(s == '[' || s == ']');
  save_and_next(ls);
  while (ls->current == '=') {
    save_and_next(ls);
    count++;
  }
  return (ls->current == s) ? count + 2
         : (count == 0) ? 1
         : 0;

}


static void read_long_string (LexState *ls, SemInfo *seminfo, size_t sep) {
  int line = ls->linenumber;  /* initial line (for error message) */
  save_and_next(ls);  /* skip 2nd '[' */
  if (currIsNewline(ls))  /* string starts with a newline? */
    inclinenumber(ls);  /* skip it */
  for (;;) {
    switch (ls->current) {
      case EOZ: {  /* error */
        const char *what = (seminfo ? "colar" : "coment\xC3\xA1rio");
        const char *msg = luaO_pushfstring(ls->L,
                     "%s longo n\xC3\xA3o finalizado (iniciado na linha %d)", what, line);
        lexerror(ls, msg, TK_EOS);
        break;  /* to avoid warnings */
      }
      case ']': {
        if (skip_sep(ls) == sep) {
          save_and_next(ls);  /* skip 2nd ']' */
          goto endloop;
        }
        break;
      }
      case '\n': case '\r': {
        save(ls, '\n');
        inclinenumber(ls);
        if (!seminfo) luaZ_resetbuffer(ls->buff);  /* avoid wasting space */
        break;
      }
      default: {
        if (seminfo) save_and_next(ls);
        else next(ls);
      }
    }
  } endloop:
  if (seminfo)
    seminfo->ts = luaX_newstring(ls, luaZ_buffer(ls->buff) + sep,
                                     luaZ_bufflen(ls->buff) - 2 * sep);
}


static void esccheck (LexState *ls, int c, const char *msg) {
  if (!c) {
    if (ls->current != EOZ)
      save_and_next(ls);  /* add current to buffer for error message */
    lexerror(ls, msg, TK_STRING);
  }
}


static int gethexa (LexState *ls) {
  save_and_next(ls);
  esccheck (ls, lisxdigit(ls->current), "digito hexadecimal esperado");
  return luaO_hexavalue(ls->current);
}


static int readhexaesc (LexState *ls) {
  int r = gethexa(ls);
  r = (r << 4) + gethexa(ls);
  luaZ_buffremove(ls->buff, 2);  /* remove saved chars from buffer */
  return r;
}


static unsigned long readutf8esc (LexState *ls) {
  unsigned long r;
  int i = 4;  /* chars to be removed: '\', 'u', '{', and first digit */
  save_and_next(ls);  /* skip 'u' */
  esccheck(ls, ls->current == '{', "faltando '{'");
  r = gethexa(ls);  /* must have at least one digit */
  while ((save_and_next(ls), lisxdigit(ls->current))) {
    i++;
    r = (r << 4) + luaO_hexavalue(ls->current);
    esccheck(ls, r <= 0x10FFFF, "valor UTF-8 muito largo");
  }
  esccheck(ls, ls->current == '}', "faltando '}'");
  next(ls);  /* skip '}' */
  luaZ_buffremove(ls->buff, i);  /* remove saved chars from buffer */
  return r;
}


static void utf8esc (LexState *ls) {
  char buff[UTF8BUFFSZ];
  int n = luaO_utf8esc(buff, readutf8esc(ls));
  for (; n > 0; n--)  /* add 'buff' to string */
    save(ls, buff[UTF8BUFFSZ - n]);
}


static int readdecesc (LexState *ls) {
  int i;
  int r = 0;  /* result accumulator */
  for (i = 0; i < 3 && lisdigit(ls->current); i++) {  /* read up to 3 digits */
    r = 10*r + ls->current - '0';
    save_and_next(ls);
  }
  esccheck(ls, r <= UCHAR_MAX, "escape decimal muito largo");
  luaZ_buffremove(ls->buff, i);  /* remove read digits from buffer */
  return r;
}


static int read_string (LexState *ls, int del, SemInfo *seminfo) {
  save_and_next(ls);  /* salva delimitador */
  while (ls->current != del) {
    switch (ls->current) {
      case EOZ:
        lexerror(ls, "colar n\xC3\xA3o finalizado", TK_EOS);
        break;
      case '\n':
      case '\r':
        if (del == '`') {
          save(ls, '\n');
          inclinenumber(ls);
        } else {
          lexerror(ls, "colar n\xC3\xA3o finalizado", TK_STRING);
        }
        break;
      case '\\': {  /* escapes */
        int c;
        save_and_next(ls);  /* salva o '\' */

        /* --- SUPORTE A ESCAPE DE ® (2 bytes) E Ⓡ (3 bytes) --- */
        if (del == '`') {
            /* Caso 1: ® (C2 AE) */
            if (ls->current == 0xC2) {
                save_and_next(ls);
                if (ls->current == 0xAE) save_and_next(ls);
                continue;
            }
            /* Caso 2: Ⓡ (E2 93 87)  */
            if (ls->current == 0xE2) {
                save_and_next(ls);
                if (ls->current == 0x93) {
                    save_and_next(ls);
                    if (ls->current == 0x87) save_and_next(ls);
                }
                continue;
            }
        }
        /* ----------------------------------------------------- */

        switch (ls->current) {
          case 'a': c = '\a'; goto read_save;
          case 'b': c = '\b'; goto read_save;
          case 'f': c = '\f'; goto read_save;
          case 'n': c = '\n'; goto read_save;
          case 'r': c = '\r'; goto read_save;
          case 't': c = '\t'; goto read_save;
          case 'v': c = '\v'; goto read_save;
          case 'x': c = readhexaesc(ls); goto read_save;
          case 'u': utf8esc(ls);  goto no_save;
          case '\n': case '\r':
            inclinenumber(ls); c = '\n'; goto only_save;
          case '\\': case '\"': case '\'':
            c = ls->current; goto read_save;
          case EOZ: goto no_save;
          case 'z': {
            luaZ_buffremove(ls->buff, 1);
            next(ls);
            while (lisspace(ls->current)) {
              if (currIsNewline(ls)) inclinenumber(ls);
              else next(ls);
            }
            goto no_save;
          }
          default: {
            esccheck(ls, lisdigit(ls->current), "sequ\xC3\xAAncia de escape inv\xC3\xA1lida");
            c = readdecesc(ls);
            goto only_save;
          }
        }
       read_save:
         next(ls);
       only_save:
         luaZ_buffremove(ls->buff, 1);
         save(ls, c);
       no_save: break;
      }
      default:
        save_and_next(ls);
    }
  }
  save_and_next(ls);  /* skip delimiter */
  seminfo->ts = luaX_newstring(ls, luaZ_buffer(ls->buff) + 1,
                                   luaZ_bufflen(ls->buff) - 2);
  return 0;
}


static int llex (LexState *ls, SemInfo *seminfo) {
  luaZ_resetbuffer(ls->buff);

  /* Se há um TK_STRING pendente de um gabarito literal,
     devolve-o agora. */
  if (ls->tem_gabarito) {
    ls->tem_gabarito = 0;
    ls->tokenstart = ls->gabarito_start;
    if (seminfo != NULL)
      *seminfo = ls->gabarito_seminfo;
    return TK_STRING;
  }

  for (;;) {
    ls->tokenstart = ls->offset;
    switch (ls->current) {
      case '\n': case '\r': {  /* line breaks */
        inclinenumber(ls);
        break;
      }
      case ' ': case '\f': case '\t': case '\v': {  /* spaces */
        next(ls);
        break;
      }
      case '-': {  /* '-' or '--' (comment) */
        next(ls);
        if (ls->current != '-') return '-';
        /* else is a comment */
        next(ls);
        if (ls->current == '[') {  /* long comment? */
          size_t sep = skip_sep(ls);
          luaZ_resetbuffer(ls->buff);  /* 'skip_sep' may dirty the buffer */
          if (sep >= 2) {
            read_long_string(ls, NULL, sep);  /* skip long comment */
            luaZ_resetbuffer(ls->buff);  /* previous call may dirty the buff. */
            break;
          }
        }
        /* else short comment */
        while (!currIsNewline(ls) && ls->current != EOZ)
          next(ls);  /* skip until end of line (or end of file) */
        break;
      }
      case '[': {  /* long string or simply '[' */
        size_t sep = skip_sep(ls);
#ifdef SANTAFE_DADOS_V3
        /* Pelo menos um '=': [[1],[2]] continua sendo lista de listas. */
        if (sep >= 3) {
#else
        if (sep >= 2) {
#endif
          read_long_string(ls, seminfo, sep);
          return TK_STRING;
        }
        else if (sep == 0)  /* '[=...' missing second bracket */
          lexerror(ls, "delimitador de colar longo inv\xC3\xA1lido", TK_STRING);
        return '[';
      }
      case '=': {
        next(ls);
        if (check_next1(ls, '=')) return TK_EQ;
        else return '=';
      }
      case '<': {
        next(ls);
        if (check_next1(ls, '=')) return TK_LE;
        else if (check_next1(ls, '<')) return TK_SHL;
        else return '<';
      }
      case '>': {
        next(ls);
        if (check_next1(ls, '=')) return TK_GE;
        else if (check_next1(ls, '>')) return TK_SHR;
        else return '>';
      }
      case '/': {
        next(ls);
        if (check_next1(ls, '/')) return TK_IDIV;
        else return '/';
      }
      case '~': {
        next(ls);
        if (check_next1(ls, '=')) return TK_NE;
        else return '~';
      }
      case ':': {
        next(ls);
        if (check_next1(ls, ':')) return TK_DBCOLON;
        else return ':';
      }
      case '`': {  /* gabarito literal estilo JS */
        ls->gabarito_start = ls->tokenstart;
        /* Lê o conteúdo entre crases como uma string normal,
           armazenando em gabarito_seminfo. */
        if (read_string(ls, ls->current, &ls->gabarito_seminfo)) {
          *seminfo = ls->gabarito_seminfo;
          return TK_STRING;
        }

        /* Marca que o PRÓXIMO token deve ser a string lida acima. */
        ls->tem_gabarito = 1;

        /* Este token atual vira o nome da função global "__gabarito". */
        {
          TString *ts = luaS_newliteral(ls->L, "__gabarito");
          seminfo->ts = ts;
        }
        return TK_NAME;  /* parser verá: __gabarito "conteúdo..." */
      }

      case '"': case '\'': {  /* short literal strings */
        read_string(ls, ls->current, seminfo);
        return TK_STRING;
      }

      case '.': {  /* '.', '..', '...', or number */
        save_and_next(ls);
        if (check_next1(ls, '.')) {
          if (check_next1(ls, '.'))
            return TK_DOTS;   /* '...' */
          else return TK_CONCAT;   /* '..' */
        }
        else if (!lisdigit(ls->current)) return '.';
        else return read_numeral(ls, seminfo);
      }
      case '0': case '1': case '2': case '3': case '4':
      case '5': case '6': case '7': case '8': case '9': {
        return read_numeral(ls, seminfo);
      }
      case EOZ: {
        return TK_EOS;
      }
      default: {  /*ACEITAR IDENTIFICADORES UNICODE UTF8*/

        if ((((0x80&ls->current)||lislalpha(ls->current))&&ls->current!=-1)) {  /*lislalpha(ls->current)) {  / ** IDENTIFICADOR OU PALAVRA RESERVADA? * /*/
          TString *ts;
          do {
            save_and_next(ls);
          } while ((((0x80&ls->current)||lislalnum(ls->current))&&ls->current!=-1)); /*lislalnum(ls->current)); / **puts(" <<\n");* /*/
          ts = luaX_newstring(ls, luaZ_buffer(ls->buff),
                                  luaZ_bufflen(ls->buff));
          seminfo->ts = ts;
          if (isreserved(ts))  /* reserved word? */
            return ts->extra - 1 + FIRST_RESERVED;
          else {
            return TK_NAME;
          }
        }

        else {  /* single-char tokens (+ - / ...) */
          int c = ls->current;
          next(ls);
          return c;
        }
      }
    }
  }
}


static void scan_token (LexState *ls, Token *token) {
  ls->scanning = 1;
  token->token = llex(ls, &token->seminfo);
  token->start = ls->tokenstart;
  token->end = ls->offset;
  ls->scanning = 0;
}


void luaX_next (LexState *ls) {
  ls->lastline = ls->linenumber;
  if (ls->lookahead.token != TK_EOS) {  /* is there a look-ahead token? */
    ls->t = ls->lookahead;  /* use this one */
    ls->lookahead.token = TK_EOS;  /* and discharge it */
  }
  else
    scan_token(ls, &ls->t);  /* read next token with its own source interval */
}


int luaX_lookahead (LexState *ls) {
  lua_assert(ls->lookahead.token == TK_EOS);
  scan_token(ls, &ls->lookahead);
  return ls->lookahead.token;
}


/* Tooling uses precisely the compiler lexer. Keep all allocations inside a
** protected call: the caller frees Mbuffer on success, syntax error and OOM.
** The partial output and source/name remain anchored on the caller's stack.
** No parser, user reader, module loader or generated function is executed.
*/
typedef struct LexemesInput {
  const char *text;
  size_t length;
  size_t remaining;
  Mbuffer buffer;
  lua_Diagnostic diagnostic;
  lua_Integer limit;
  lua_Integer work;
  int limited;
} LexemesInput;

static const char *lexemes_reader (lua_State *L, void *data, size_t *size) {
  LexemesInput *input = (LexemesInput *)data;
  (void)L;
  *size = input->remaining;
  input->remaining = 0;
  return *size ? input->text : NULL;
}

/* Raw template intervals. Match the runtime's brace balancing exactly; escape
** decoding can move/synthesize delimiters, so consumers must treat templates
** containing escapes conservatively. Each byte is visited at most twice. */
static int lexemes_template (LexState *ls, LexemesInput *input, const char *s, size_t n, size_t base) {
  lua_State *L = ls->L;
  size_t i = 1;
  lua_Integer count = 0;
  int incomplete = 0;
#ifdef SANTAFE_DADOS_V3
  lua_createlist(L, 0);
#else
  lua_newtable(L);
#endif
  while (i + 1 < n) {
    size_t marker = 0, start, end;
    int expression = 0;
    if (s[i] == '\\') { i += 2; continue; }
    if ((unsigned char)s[i] == 0xc2 && (unsigned char)s[i+1] == 0xae) marker = 2;
    else if (i + 2 < n && (unsigned char)s[i] == 0xe2 &&
             (unsigned char)s[i+1] == 0x93 && (unsigned char)s[i+2] == 0x87) marker = 3;
    if (!marker) { i++; continue; }
    start = i + marker;
    if (start < n - 1 && s[start] == '{') {
      size_t depth = 1, j = ++start;
      expression = 1;
      while (j < n - 1 && depth) {
        if (s[j] == '{') depth++;
        else if (s[j] == '}') depth--;
        j++;
      }
      if (depth) { incomplete = 1; break; }
      end = j - 1; i = j;
    }
    else {
      end = start + luaU_identifier(s + start, n - 1 - start);
      i = end;
      if (end == start) continue;
    }
    if (++input->work > input->limit) {
      input->limited = 1;
      luaX_syntaxerror(ls, "limite de lexemas/interpolacoes excedido");
    }
    lua_createtable(L, 0, 3);
    lua_pushinteger(L, (lua_Integer)(base + start)); lua_setfield(L, -2, "in\xC3\xAD" "cio");
    lua_pushinteger(L, (lua_Integer)(base + end)); lua_setfield(L, -2, "fim");
    lua_pushboolean(L, expression); lua_setfield(L, -2, "express\xC3\xA3o");
    lua_rawseti(L, -2, ++count);
  }
  return incomplete;
}

static int lexemes_worker (lua_State *L) {
  LexemesInput *input = (LexemesInput *)lua_touserdata(L, 4);
  LexState ls;
  ZIO z;
  lua_Integer count = 0;
  /* Reuse the string anchored in argument 2. luaS_new creates a distinct
     object for long names: a bare C pointer would be collected during the
     scan, then dereferenced when reporting a lexical error/limit. */
  TString *source = tsvalue(L->ci->func + 2);
  memset(&ls, 0, sizeof(ls));
  ls.buff = &input->buffer;
  lua_newtable(L);  /* lexer string anchors, alive for the entire scan */
  ls.h = hvalue(L->top - 1);
  luaZ_init(L, &z, lexemes_reader, input);
  z.diagnostic = &input->diagnostic;
  luaX_setinput(L, &ls, &z, source, zgetc(&z));
  for (;;) {
    const char *kind;
    luaX_next(&ls);
    if (ls.t.token == TK_EOS) break;
    if (++input->work > input->limit) {
      input->limited = 1;
      luaX_syntaxerror(&ls, "limite de lexemas excedido");
    }
    if (ls.tem_gabarito) {
      luaX_next(&ls);  /* collapse synthetic __gabarito + string into one token */
      kind = "gabarito";
    }
    else if (ls.t.token == TK_NAME) kind = "nome";
    else if (ls.t.token == TK_STRING) kind = "colar";
    else if (ls.t.token == TK_INT || ls.t.token == TK_FLT) kind = "n\xC3\xBAmero";
    else if (ls.t.token >= FIRST_RESERVED && ls.t.token <= TK_WHILE) kind = "palavra";
    else kind = "s\xC3\xADmbolo";
    lua_createtable(L, 0, 5);
    lua_pushstring(L, kind);
    lua_setfield(L, -2, "tipo");
    lua_pushinteger(L, (lua_Integer)ls.t.start);
    lua_setfield(L, -2, "in\xC3\xAD" "cio");
    lua_pushinteger(L, (lua_Integer)ls.t.end);
    lua_setfield(L, -2, "fim");
    lua_pushlstring(L, input->text + ls.t.start, ls.t.end - ls.t.start);
    lua_setfield(L, -2, "texto");
    if (strcmp(kind, "gabarito") == 0) {
      int incomplete = lexemes_template(&ls, input, input->text + ls.t.start, ls.t.end - ls.t.start, ls.t.start);
      lua_setfield(L, -2, "interpola\xC3\xA7\xC3\xB5" "es");
      lua_pushboolean(L, incomplete); lua_setfield(L, -2, "gabaritoIncompleto");
    }
    if (ls.t.token == TK_NAME || ls.t.token == TK_STRING) {
      lua_pushlstring(L, getstr(ls.t.seminfo.ts), tsslen(ls.t.seminfo.ts));
      lua_setfield(L, -2, "valor");
    }
    if (ls.t.token == TK_NAME) {
      lua_pushinteger(L, (lua_Integer)luaU_identifier(input->text + ls.t.start,
                                                     ls.t.end - ls.t.start));
      lua_setfield(L, -2, "octetosIdentificador");
    }
    lua_rawseti(L, 3, ++count);
  }
  return 0;
}

int luaX_lexemes (lua_State *L) {
  LexemesInput input;
  int status;
  memset(&input, 0, sizeof(input));
  luaL_checktype(L, 1, LUA_TSTRING);
  input.text = lua_tolstring(L, 1, &input.length);
  luaL_argcheck(L, input.length <= 16 * 1024 * 1024, 1,
                "fonte excede 16 MiB");
  input.remaining = input.length;
  input.limit = luaL_optinteger(L, 3, 100000);
  luaL_argcheck(L, input.limit >= 1 && input.limit <= 1000000, 3,
                "limite deve estar entre 1 e 1000000");
  lua_settop(L, 3);
  lua_pushstring(L, luaL_optstring(L, 2, "=(lexemas)"));
  lua_replace(L, 2);
  lua_settop(L, 2);
#ifdef SANTAFE_DADOS_V3
  lua_createlist(L, 0);  /* result stays anchored here across pcall */
#else
  lua_newtable(L);
#endif
  lua_pushcfunction(L, lexemes_worker);
  lua_pushvalue(L, 1);
  lua_pushvalue(L, 2);
  lua_pushvalue(L, 3);
  lua_pushlightuserdata(L, &input);
  status = lua_pcall(L, 4, 0, 0);
  luaZ_freebuffer(L, &input.buffer);
  if (status == LUA_OK) return 1;
  if (status != LUA_ERRSYNTAX) luaD_throw(L, status);
  lua_newtable(L);
  lua_pushvalue(L, -2);
  lua_setfield(L, -2, "mensagem");
  lua_pushstring(L, input.limited ? "limite-lexemas" : "lexico");
  lua_setfield(L, -2, "c\xC3\xB3" "digo");
  lua_pushinteger(L, (lua_Integer)input.diagnostic.start);
  lua_setfield(L, -2, "in\xC3\xAD" "cio");
  lua_pushinteger(L, (lua_Integer)input.diagnostic.end);
  lua_setfield(L, -2, "fim");
  lua_remove(L, -2);  /* original error; return partial stream + diagnostic */
  return 2;
}
