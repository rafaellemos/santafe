/*
 * SantaFé 1.0 - ponte WebAssembly / Emscripten
 *
 * Interface usada pelo navegador:
 *   sf_init()
 *   sf_run_code(const char *codigo)
 *
 * Esta versão foi reconstituída a partir da última interface WASM usada
 * no projeto e ajustada para compilar contra os headers reais do núcleo
 * SantaFé/Lua 5.3 (lua.h, lauxlib.h, lualib.h).
 *
 * A captura de saída (mostre/es -> #outputView) é feita via
 * js_append_output(), amarrada a lua_writestring/lua_writeline através
 * dos -D no emscripten.sh (ver sf_wasm_writestring/sf_wasm_writeline).
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <emscripten.h>

#include "lua.h"
#include "lauxlib.h"
#include "lualib.h"

static lua_State *sf_L = NULL;

/* Escreve texto (já terminado em nulo) na #outputView do navegador. */
EM_JS(void, js_append_output, (const char *msg), {
  const term = document.getElementById("outputView");
  if (term) term.textContent += UTF8ToString(msg);
});

/*
 * Ponte para lua_writestring/lua_writeline (redefinidas via -D em
 * emscripten.sh). Trechos vindos de mostre()/es.escreva() não são
 * terminados em nulo (colar é seguro para dados binários), então copiamos para um
 * buffer temporário antes de cruzar para JS, que espera uma C-string.
 */
void sf_wasm_writestring(const char *s, size_t l) {
  char *buf = (char *)malloc(l + 1);
  if (buf == NULL) return;
  memcpy(buf, s, l);
  buf[l] = '\0';
  js_append_output(buf);
  free(buf);
}

void sf_wasm_writeline(void) {
  sf_wasm_writestring("\n", 1);
}

/*
 * Envia erros para a mesma #outputView (é onde o usuário está olhando)
 * e também para o console, para quem estiver com o devtools aberto.
 */
EM_JS(void, sf_erro_js, (const char *msg), {
  const texto = UTF8ToString(msg);
  const term = document.getElementById("outputView");
  if (term) term.textContent += texto + "\n";
  if (typeof Module !== 'undefined' && typeof Module.printErr === 'function') {
    Module.printErr(texto);
  } else {
    console.error(texto);
  }
});

/*
 * Inicializa uma única VM SantaFé.
 * Retorna 0 em sucesso e valor diferente de zero em erro.
 */
EMSCRIPTEN_KEEPALIVE
int sf_init(void) {
  if (sf_L != NULL)
    return 0;

  sf_L = luaL_newstate();
  if (sf_L == NULL) {
    sf_erro_js("SantaFé: não foi possível criar o estado da VM.");
    return 1;
  }

  luaL_openlibs(sf_L);
  return 0;
}

/*
 * Executa um trecho de código SantaFé recebido do JavaScript.
 * O parser do núcleo é o responsável pelos termos da linguagem em português.
 *
 * Retorno:
 *   0            sucesso
 *   LUA_ERR*     erro de carga/execução
 */
EMSCRIPTEN_KEEPALIVE
int sf_run_code(const char *codigo) {
  int status;

  if (codigo == NULL) {
    sf_erro_js("SantaFé: código nulo recebido por sf_run_code().");
    return LUA_ERRRUN;
  }

  if (sf_L == NULL) {
    status = sf_init();
    if (status != 0)
      return status;
  }

  /* Não deixa resultados de uma execução anterior acumularem na pilha. */
  lua_settop(sf_L, 0);

  /* Nome de chunk fixo ("=código") em vez do padrão de luaL_loadstring
     (que usa o próprio código como nome e produz erros feios do tipo
     [string "garanta(1 + 1 == 2, ..."]:4: ...). O prefixo "=" faz o Lua
     mostrar o nome literal, sem cortar/citar o conteúdo. */
  status = luaL_loadbuffer(sf_L, codigo, strlen(codigo), "=código");
  if (status == LUA_OK)
    status = lua_pcall(sf_L, 0, LUA_MULTRET, 0);

  if (status != LUA_OK) {
    const char *erro = lua_tostring(sf_L, -1);
    if (erro != NULL)
      sf_erro_js(erro);
    else
      sf_erro_js("SantaFé: erro desconhecido durante a execução.");
  }

  /* Limpa resultados/erro para a próxima chamada. */
  lua_settop(sf_L, 0);
  return status;
}
