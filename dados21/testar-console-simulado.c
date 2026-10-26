/* Contrato simulado da API Windows; não substitui execução nativa. */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef unsigned int UINT;
typedef unsigned long DWORD;
typedef void *HANDLE;
typedef long LONG;
typedef int BOOL;
#define WINAPI
#define FALSE 0
#define TRUE 1
#define CTRL_C_EVENT 0
#define CTRL_BREAK_EVENT 1
#define STD_INPUT_HANDLE 0
#define STD_OUTPUT_HANDLE 1
#define STD_ERROR_HANDLE 2
#define CP_UTF8 65001
#define INVALID_HANDLE_VALUE ((HANDLE)(intptr_t)-1)
static int consoles[3], sets_in, sets_out, exits, flushes;
static int fail_in, fail_out, fail_exit, invalid_handle, fail_handler;
static UINT in_cp, out_cp;
static void (*exit_handler)(void);
static BOOL (*control_handler)(DWORD);
static LONG InterlockedExchange(volatile LONG *p,LONG n) { LONG old=*p; *p=n; return old; }
static int SetConsoleCtrlHandler(BOOL (*fn)(DWORD), BOOL add) {
  assert(add); if (fail_handler) return 0; control_handler=fn; return 1;
}
static HANDLE GetStdHandle(DWORD which) {
  return invalid_handle ? INVALID_HANDLE_VALUE : (HANDLE)(uintptr_t)(which+1);
}
static int GetConsoleMode(HANDLE h, DWORD *mode) {
  *mode=0; return consoles[(uintptr_t)h-1];
}
static UINT GetConsoleCP(void) { return in_cp; }
static UINT GetConsoleOutputCP(void) { return out_cp; }
static int SetConsoleCP(UINT cp) {
  sets_in++; if (fail_in && cp==CP_UTF8) return 0; in_cp=cp; return 1;
}
static int SetConsoleOutputCP(UINT cp) {
  sets_out++; if (fail_out && cp==CP_UTF8) return 0; out_cp=cp; return 1;
}
static int mock_atexit(void (*fn)(void)) {
  exits++; if (fail_exit) return -1; exit_handler=fn; return 0;
}
static int mock_fflush(FILE *f) { (void)f; flushes++; return 0; }
#define SANTAFE_CONSOLE_TEST
#define atexit mock_atexit
#define fflush mock_fflush
#include "overlay/src/lwinconsole.h"
#undef atexit
#undef fflush
static void reset(int input, int output, int error) {
  consoles[0]=input; consoles[1]=output; consoles[2]=error;
  sets_in=sets_out=exits=flushes=0;
  fail_in=fail_out=fail_exit=invalid_handle=fail_handler=0;
  in_cp=out_cp=850; exit_handler=NULL;
  sf_console_input_changed=sf_console_output_changed=0;
  sf_console_evaluating=0; control_handler=NULL;
}
int main(void) {
  reset(1,1,1); assert(sf_console_prepare());
  assert(in_cp==CP_UTF8 && out_cp==CP_UTF8 && exits==1);
  exit_handler(); assert(in_cp==850 && out_cp==850 && flushes==2);
  sf_console_restore(); assert(sets_in==2 && sets_out==2);

  reset(0,0,0); assert(sf_console_prepare());
  assert(!sets_in && !sets_out && !exits); /* LSP/pipes intactos */
  reset(1,0,0); assert(sf_console_prepare());
  assert(in_cp==CP_UTF8 && out_cp==850 && !sets_out); exit_handler();
  reset(0,1,0); assert(sf_console_prepare());
  assert(in_cp==850 && out_cp==CP_UTF8 && !sets_in); exit_handler();
  reset(0,0,1); assert(sf_console_prepare());
  assert(out_cp==CP_UTF8 && !sets_in); exit_handler();

  reset(1,1,1); in_cp=out_cp=CP_UTF8; assert(sf_console_prepare());
  assert(!sets_in && !sets_out && !exits);
  reset(1,1,1); fail_exit=1; assert(!sf_console_prepare());
  assert(!sets_in && !sets_out && in_cp==850 && out_cp==850);
  reset(1,1,1); fail_in=1; assert(!sf_console_prepare());
  assert(in_cp==850 && out_cp==850 && !sets_out);
  reset(1,1,1); fail_out=1; assert(!sf_console_prepare());
  assert(in_cp==850 && out_cp==850 && !sf_console_input_changed);
  exit_handler(); assert(sets_in==2 && sets_out==1);

  reset(1,1,1); assert(sf_console_prepare());
  in_cp=out_cp=1252; exit_handler();
  assert(in_cp==1252 && out_cp==1252 && sets_in==1 && sets_out==1);
  reset(1,1,1); invalid_handle=1; assert(sf_console_prepare());
  assert(!sets_in && !sets_out && !exits);
  reset(1,1,1); in_cp=0; assert(!sf_console_prepare());
  assert(!sets_in && !sets_out && !exits);
  reset(1,1,1); fail_handler=1; assert(!sf_console_prepare());
  assert(!sets_in && !sets_out);
  reset(1,1,1); assert(sf_console_prepare());
  assert(!control_handler(CTRL_C_EVENT));
  assert(in_cp==850 && out_cp==850 && flushes==0);
  reset(1,1,1); assert(sf_console_prepare()); sf_console_evaluation(1);
  assert(!control_handler(CTRL_C_EVENT) && in_cp==CP_UTF8 && out_cp==CP_UTF8);
  sf_console_evaluation(0); assert(!control_handler(CTRL_C_EVENT));
  assert(in_cp==850 && out_cp==850);
  reset(1,1,1); assert(sf_console_prepare()); sf_console_evaluation(1);
  assert(!control_handler(CTRL_BREAK_EVENT));
  assert(in_cp==850 && out_cp==850 && flushes==0);
  puts("CONSOLE_SIMULADO_OK 16 casos; execucao Windows pendente");
  return 0;
}
