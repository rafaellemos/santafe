/* Entrada UTF-8 do console Windows. Interface interna compartilhada pelo CLI,
 * es e carregador de stdin; arquivos e pipes continuam sob responsabilidade CRT.
 * A implementação vive em lauxlib.c, inclusive na distribuição com DLL.
 * Não altera modo do console, localidade, páginas de códigos ou descritores.
 */
#ifndef SF_WININPUT_H
#define SF_WININPUT_H

#if defined(LUA_USE_WINDOWS)
LUALIB_API int sf_input_is_console(FILE *f);
LUALIB_API int sf_input_getc(FILE *f);
LUALIB_API int sf_input_ungetc(int ch, FILE *f);
LUALIB_API size_t sf_input_read(void *buffer, size_t count, FILE *f);
LUALIB_API int sf_input_eof(FILE *f);
LUALIB_API int sf_input_error(FILE *f);
LUALIB_API void sf_input_clear(FILE *f);
#else
#define sf_input_is_console(f) ((void)(f), 0)
#define sf_input_getc(f) getc(f)
#define sf_input_ungetc(c,f) ungetc((c),(f))
#define sf_input_read(p,n,f) fread((p),1,(n),(f))
#define sf_input_eof(f) feof(f)
#define sf_input_error(f) ferror(f)
#define sf_input_clear(f) clearerr(f)
#endif

#if defined(LUA_USE_WINDOWS) && defined(SF_WININPUT_IMPLEMENTATION)
#ifndef SF_WININPUT_TEST
#include <windows.h>
#include <io.h>
#endif
#include <errno.h>
#include <stdint.h>
#include <string.h>

typedef struct {
  HANDLE handle;
  /* Em modo de linha o tamanho pedido também limita a edição no conhost.
   * Um bloco pequeno descarta texto digitado antes de devolver CRLF. Usar a
   * mesma capacidade de 16K adotada por CPython, mesmo para es.leia(1). */
  WCHAR wide[16384];
  DWORD next, length;
  unsigned char bytes[4];
  unsigned int byte_next, byte_length;
  int pushed, has_pushed, eof, error, skip_lf;
} sf_InputConsole;
static sf_InputConsole sf_input_console;

static HANDLE sf_input_handle(FILE *f) {
  DWORD mode;
  HANDLE h;
  /* Somente stdin: não confundir arquivos, pipes, NUL ou pseudoterminais com
   * um console. O descritor CRT é a autoridade, mesmo após freopen/dup2. */
  if (f != stdin) return INVALID_HANDLE_VALUE;
  h = (HANDLE)_get_osfhandle(_fileno(f));
  if (h == INVALID_HANDLE_VALUE || h == NULL || !GetConsoleMode(h, &mode))
    return INVALID_HANDLE_VALUE;
  return h;
}

LUALIB_API int sf_input_is_console(FILE *f) {
  return sf_input_handle(f) != INVALID_HANDLE_VALUE;
}

/* Os chamadores seguram a trava do FILE; todas as unidades usam este estado. */
static sf_InputConsole *sf_input_state(HANDLE handle) {
  sf_InputConsole *s = &sf_input_console;
  if (s->handle != handle) {
    memset(s, 0, sizeof(*s));
    s->handle = handle;
  }
  return s;
}

static int sf_input_unit(sf_InputConsole *s) {
  if (s->error || s->eof) return EOF;
  if (s->next == s->length) {
    DWORD n = 0, mode;
    DWORD error;
    int ok;
    SetLastError(0);
    ok = ReadConsoleW(s->handle, s->wide,
                      (DWORD)(sizeof(s->wide)/sizeof(s->wide[0])), &n, NULL);
    error = GetLastError();
    /* Algumas versões do conhost devolvem TRUE com operação cancelada e
     * contagem zero ou DWORD(-1). Não tratar cancelamento como EOF nem usar
     * uma contagem fora do buffer. */
    if (!ok || error == ERROR_OPERATION_ABORTED) {
      s->error = error == ERROR_OPERATION_ABORTED ? EINTR : EIO;
      errno = s->error;
      return EOF;
    }
    if (n > sizeof(s->wide)/sizeof(s->wide[0])) {
      errno = s->error = EIO; return EOF;
    }
    if (!n) { s->eof = 1; return EOF; }
    /* O editor nativo pode descartar o excesso de uma linha cheia. Recusar
     * a fronteira conservadoramente, antes de executar um comando truncado.
     * Arquivos/pipes não usam este limite; modo sem edição aceita blocos. */
    if (!GetConsoleMode(s->handle, &mode)) {
      errno = s->error = EIO; return EOF;
    }
    if ((mode & ENABLE_LINE_INPUT) && n >= 16383) {
      errno = s->error = EOVERFLOW; return EOF;
    }
    s->next = 0; s->length = n;
  }
  return (unsigned short)s->wide[s->next++];
}

static int sf_input_byte(sf_InputConsole *s) {
  int unit;
  uint32_t cp;
  if (s->has_pushed) { s->has_pushed = 0; return s->pushed; }
  if (s->byte_next < s->byte_length) return s->bytes[s->byte_next++];
  if (s->error) { errno = s->error; return EOF; }
  do {
    unit = sf_input_unit(s);
    if (unit == EOF) return EOF;
    if (s->skip_lf) {
      s->skip_lf = 0;
      if (unit == '\n') continue;
    }
    break;
  } while (1);
  /* Convenção de EOF do console em modo texto (Ctrl+Z, Enter). */
  if (unit == 26) { s->eof = 1; s->next = s->length; return EOF; }
  /* A leitura textual tem a mesma normalização CRLF da CRT. Não espera outra
   * linha quando CR é a última unidade disponível. */
  if (unit == '\r') { s->skip_lf = 1; return '\n'; }
  cp = (uint32_t)unit;
  if (cp >= 0xd800 && cp <= 0xdbff) {
    int low = sf_input_unit(s);
    if (low < 0xdc00 || low > 0xdfff) {
      if (!s->error) s->error = EILSEQ;
      errno = s->error;
      return EOF;
    }
    cp = 0x10000 + ((cp - 0xd800) << 10) + (uint32_t)(low - 0xdc00);
  }
  else if (cp >= 0xdc00 && cp <= 0xdfff) {
    errno = s->error = EILSEQ; return EOF;
  }
  /* Conversão estrita UTF-16 -> UTF-8; não substitui caracteres nem perde
   * bytes em es.leia(1), no retorno do leitor numérico ou entre chamadas. */
  if (cp < 0x80) return (int)cp;
  if (cp < 0x800) {
    s->bytes[0] = 0xc0 | (cp >> 6);
    s->byte_length = 2;
  }
  else if (cp < 0x10000) {
    s->bytes[0] = 0xe0 | (cp >> 12);
    s->bytes[1] = 0x80 | ((cp >> 6) & 63);
    s->byte_length = 3;
  }
  else {
    s->bytes[0] = 0xf0 | (cp >> 18);
    s->bytes[1] = 0x80 | ((cp >> 12) & 63);
    s->bytes[2] = 0x80 | ((cp >> 6) & 63);
    s->byte_length = 4;
  }
  s->bytes[s->byte_length-1] = 0x80 | (cp & 63);
  s->byte_next = 1;
  return s->bytes[0];
}

LUALIB_API int sf_input_getc(FILE *f) {
  HANDLE h; int ch;
  _lock_file(f);
  h = sf_input_handle(f);
  ch = h == INVALID_HANDLE_VALUE ? getc(f) : sf_input_byte(sf_input_state(h));
  _unlock_file(f);
  return ch;
}

LUALIB_API int sf_input_ungetc(int ch, FILE *f) {
  HANDLE h;
  _lock_file(f);
  h = sf_input_handle(f);
  if (h == INVALID_HANDLE_VALUE) ch = ungetc(ch, f);
  else {
    sf_InputConsole *s = sf_input_state(h);
    if (ch == EOF || s->has_pushed) ch = EOF;
    else {
      s->pushed = ch = (unsigned char)ch;
      s->has_pushed = 1; s->eof = 0;
    }
  }
  _unlock_file(f);
  return ch;
}

LUALIB_API size_t sf_input_read(void *buffer, size_t count, FILE *f) {
  HANDLE h; size_t n = 0;
  _lock_file(f);
  h = sf_input_handle(f);
  if (h == INVALID_HANDLE_VALUE) n = fread(buffer, 1, count, f);
  else {
    sf_InputConsole *s = sf_input_state(h);
    int ch;
    while (n < count && (ch = sf_input_byte(s)) != EOF)
      ((unsigned char *)buffer)[n++] = (unsigned char)ch;
  }
  _unlock_file(f);
  return n;
}

LUALIB_API int sf_input_eof(FILE *f) {
  HANDLE h; int eof;
  _lock_file(f);
  h = sf_input_handle(f);
  eof = h == INVALID_HANDLE_VALUE ? feof(f) : sf_input_state(h)->eof;
  _unlock_file(f);
  return eof;
}

LUALIB_API int sf_input_error(FILE *f) {
  HANDLE h; int error;
  _lock_file(f);
  h = sf_input_handle(f);
  error = h == INVALID_HANDLE_VALUE ? ferror(f) : sf_input_state(h)->error;
  if (h != INVALID_HANDLE_VALUE && error) errno = error;
  _unlock_file(f);
  return error;
}

LUALIB_API void sf_input_clear(FILE *f) {
  HANDLE h;
  _lock_file(f);
  h = sf_input_handle(f);
  clearerr(f);
  if (h != INVALID_HANDLE_VALUE) {
    sf_InputConsole *s = sf_input_state(h);
    s->eof = 0; s->error = 0;
  }
  _unlock_file(f);
}
#endif
#endif
