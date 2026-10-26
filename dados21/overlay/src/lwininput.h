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
/* Ciclo exclusivo do CLI; a biblioteca não instala tratadores de sinais. */
LUALIB_API int sf_input_evaluation(int active);
LUALIB_API void sf_input_interrupt(void);
LUALIB_API void sf_input_shutdown(void);
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
#ifdef SF_WININPUT_TRACE
#define SF_INPUT_TRACE(...) fprintf(stderr, __VA_ARGS__)
#else
#define SF_INPUT_TRACE(...) ((void)0)
#endif

#ifndef SF_WININPUT_TEST
/* Um evento por processo CLI, compartilhado também na versão DLL. Nenhum
 * descritor de arquivo/pipe passa pela rotina de cancelamento do console. */
static HANDLE sf_input_cancel_event;
static int sf_input_active;
LUALIB_API int sf_input_evaluation(int active) {
  if (active && sf_input_is_console(stdin) && !sf_input_cancel_event) {
    sf_input_cancel_event = CreateEventW(NULL, TRUE, FALSE, NULL);
    if (!sf_input_cancel_event) return 0;
  }
  if (sf_input_cancel_event && !ResetEvent(sf_input_cancel_event)) return 0;
  SF_INPUT_TRACE("INPUT evaluation=%d\n", active);
  sf_input_active = active;
  return 1;
}
LUALIB_API void sf_input_interrupt(void) {
  /* Chamada pelo tratador SIGINT: sem stdio, alocação ou trava do FILE. */
  if (sf_input_cancel_event) SetEvent(sf_input_cancel_event);
}
LUALIB_API void sf_input_shutdown(void) {
  if (sf_input_cancel_event) CloseHandle(sf_input_cancel_event);
  sf_input_cancel_event = NULL;
  sf_input_active = 0;
}

typedef struct {
  HANDLE input;
  WCHAR *buffer;
  DWORD capacity, count, error;
  BOOL ok;
} sf_InputRead;
static DWORD WINAPI sf_input_reader(LPVOID argument) {
  sf_InputRead *r = (sf_InputRead *)argument;
  if (WaitForSingleObject(sf_input_cancel_event, 0) == WAIT_OBJECT_0) {
    r->error = ERROR_OPERATION_ABORTED; return 0;
  }
  SetLastError(0);
  r->ok = ReadConsoleW(r->input, r->buffer, r->capacity, &r->count, NULL);
  r->error = GetLastError();
  return 0;
}
static int sf_input_readwide(HANDLE input, WCHAR *buffer, DWORD capacity,
                             DWORD *count) {
  sf_InputRead r;
  HANDLE waits[2], thread;
  DWORD waited;
  SF_INPUT_TRACE("INPUT readwide active=%d\n", sf_input_active);
  if (!sf_input_active || !sf_input_cancel_event) {
    int direct = ReadConsoleW(input, buffer, capacity, count, NULL);
    DWORD err = GetLastError();
    SF_INPUT_TRACE("INPUT direct ok=%d count=%lu err=%lu\n",direct,(unsigned long)*count,(unsigned long)err);
    SetLastError(err); return direct;
  }
retry_read:
  if (WaitForSingleObject(sf_input_cancel_event, 0) == WAIT_OBJECT_0) {
    *count = 0; SetLastError(ERROR_OPERATION_ABORTED); return 0;
  }
  memset(&r, 0, sizeof(r));
  r.input = input; r.buffer = buffer; r.capacity = capacity;
  /* O auxiliar executa somente esta ReadConsoleW. Ao contrário de cancelar
   * a thread principal, nunca cancela outra operação iniciada em seguida. */
  thread = CreateThread(NULL, 0, sf_input_reader, &r, 0, NULL);
  if (!thread) return 0;
  waits[0] = thread; waits[1] = sf_input_cancel_event;
  waited = WaitForMultipleObjects(2, waits, FALSE, INFINITE);
  if (waited != WAIT_OBJECT_0) {
    DWORD failure = waited == WAIT_OBJECT_0 + 1
                  ? ERROR_OPERATION_ABORTED : GetLastError();
    /* O sinal pode anteceder a entrada efetiva na syscall. Repetir até a
     * conclusão cobre essa janela; não liberar buffer nem encerrar thread
     * à força enquanto o sistema ainda o utiliza. */
    do { CancelSynchronousIo(thread); }
    while (WaitForSingleObject(thread, 10) != WAIT_OBJECT_0);
    r.ok = FALSE; r.error = failure ? failure : ERROR_INVALID_FUNCTION;
  }
  CloseHandle(thread);
  if (r.error == ERROR_OPERATION_ABORTED) {
    /* Ctrl+C pelo terminal cancela ReadConsoleW antes de a thread SIGINT
     * publicar o gancho. Não devolver EINTR ainda: docall poderia restaurar
     * SIG_DFL e o mesmo sinal terminaria o processo. Aguardar brevemente o
     * evento do tratador; sem sinal, recomeçar a leitura, mantendo SIGINT
     * instalado e a espera cancelável. O prazo não é uma condição de êxito.
     * Também cobre o console que apenas cancela/limpa a linha sem sinal. */
    waited = WaitForSingleObject(sf_input_cancel_event, 100);
    if (waited == WAIT_TIMEOUT) goto retry_read;
    if (waited != WAIT_OBJECT_0) {
      r.ok = FALSE; r.error = ERROR_INVALID_FUNCTION;
    }
  }
  SF_INPUT_TRACE("INPUT worker ok=%d count=%lu err=%lu\n",r.ok,(unsigned long)r.count,(unsigned long)r.error);
  *count = r.count;
  SetLastError(r.error);
  return r.ok;
}
#else
/* O simulador verifica conversão/fronteiras; cancelamento é ensaiado no
 * Windows nativo com threads e sinais reais, nas duas distribuições. */
#define sf_input_readwide(h,b,n,c) ReadConsoleW((h),(b),(n),(c),NULL)
#endif

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
    ok = sf_input_readwide(s->handle, s->wide,
                      (DWORD)(sizeof(s->wide)/sizeof(s->wide[0])), &n);
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
