/* Console interativo Windows: UTF-8 durante a execução, sem mudar pipes.
 * Usado apenas pelo executável CLI; não pelo iniciador do SLS.
 * Não altera registro, localidade da máquina, modo binário ou fonte do terminal.
 */
#ifndef SF_WINCONSOLE_H
#define SF_WINCONSOLE_H

#ifndef SANTAFE_CONSOLE_TEST
#include <windows.h>
#endif
#include <stdio.h>
#include <stdlib.h>

static UINT sf_console_input_before;
static UINT sf_console_output_before;
static int sf_console_input_changed;
static int sf_console_output_changed;
static volatile LONG sf_console_evaluating;

static void sf_console_evaluation(int active) {
  InterlockedExchange(&sf_console_evaluating, active);
}

/* Ctrl+C durante código mantém o tratamento SIGINT do interpretador. Na
 * espera por entrada e em Ctrl+Break, a CRT pode terminar sem chamar atexit.
 * A rotina de controle não usa stdio/travas: apenas devolve as páginas e
 * deixa a propagação normal do sinal prosseguir. */
static BOOL WINAPI sf_console_control(DWORD event) {
  if (event == CTRL_BREAK_EVENT ||
      (event == CTRL_C_EVENT && !sf_console_evaluating)) {
    if (sf_console_output_changed && GetConsoleOutputCP() == CP_UTF8)
      SetConsoleOutputCP(sf_console_output_before);
    if (sf_console_input_changed && GetConsoleCP() == CP_UTF8)
      SetConsoleCP(sf_console_input_before);
  }
  return FALSE;
}

static int sf_console_is_handle(DWORD which) {
  DWORD mode;
  HANDLE handle = GetStdHandle(which);
  return handle != NULL && handle != INVALID_HANDLE_VALUE &&
         GetConsoleMode(handle, &mode);
}

static void sf_console_restore(void) {
  if (sf_console_output_changed) {
    fflush(stdout);
    fflush(stderr);
    /* Preserve uma mudança explícita feita durante a execução. */
    if (GetConsoleOutputCP() == CP_UTF8)
      SetConsoleOutputCP(sf_console_output_before);
    sf_console_output_changed = 0;
  }
  if (sf_console_input_changed) {
    if (GetConsoleCP() == CP_UTF8)
      SetConsoleCP(sf_console_input_before);
    sf_console_input_changed = 0;
  }
}

static int sf_console_prepare(void) {
  int input = sf_console_is_handle(STD_INPUT_HANDLE);
  int output = sf_console_is_handle(STD_OUTPUT_HANDLE) ||
               sf_console_is_handle(STD_ERROR_HANDLE);
  int change_input, change_output;
  if (!input && !output) return 1;
  sf_console_input_before = input ? GetConsoleCP() : CP_UTF8;
  sf_console_output_before = output ? GetConsoleOutputCP() : CP_UTF8;
  if (!sf_console_input_before || !sf_console_output_before) return 0;
  change_input = input && sf_console_input_before != CP_UTF8;
  change_output = output && sf_console_output_before != CP_UTF8;
  if (!change_input && !change_output) return 1;
  /* Registre a reversão antes de qualquer alteração; cobre também os.exit. */
  if (atexit(sf_console_restore) != 0) return 0;
  if (!SetConsoleCtrlHandler(sf_console_control, TRUE)) return 0;
  if (change_input) {
    if (!SetConsoleCP(CP_UTF8)) return 0;
    sf_console_input_changed = 1;
  }
  if (change_output) {
    if (!SetConsoleOutputCP(CP_UTF8)) {
      sf_console_restore();
      return 0;
    }
    sf_console_output_changed = 1;
  }
  return 1;
}

#endif
