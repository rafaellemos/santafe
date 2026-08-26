/*
 * segredo.c
 * Proteção de senhas e bilhetes opacos para Santafé.
 *
 * As senhas usam Argon2id pelo formato autocontido da libsodium. O trabalho
 * deliberadamente caro ocorre numa thread; somente o retorno toca a VM.
 */

#include <gio/gio.h>
#include <sodium.h>
#include <stdio.h>
#include <string.h>

#include "lua.h"
#include "lauxlib.h"

#define SEGREDO_MEMORIA (19U * 1024U * 1024U)
#define SEGREDO_ITERACOES 2U
#define SEGREDO_RESUMO_TACOS 32U

typedef enum {
    TRABALHO_PROTEGER_SENHA,
    TRABALHO_CONFERIR_SENHA
} tipo_trabalho_t;

typedef struct {
    lua_State *L;
    int tratador_ref;
    int dado_ref;
    tipo_trabalho_t tipo;
    unsigned char *senha;
    size_t senha_tamanho;
    char *resumo;
} trabalho_t;

typedef struct {
    gboolean sucesso;
    gboolean confere;
    char resumo[crypto_pwhash_STRBYTES];
    char *falha;
} resultado_t;

static void liberar_resultado(gpointer ponteiro) {
    resultado_t *resultado = (resultado_t *)ponteiro;
    if (!resultado) return;
    g_free(resultado->falha);
    sodium_memzero(resultado, sizeof(*resultado));
    g_free(resultado);
}

static void liberar_trabalho(trabalho_t *trabalho) {
    if (!trabalho) return;
    if (trabalho->senha) {
        sodium_memzero(trabalho->senha, trabalho->senha_tamanho);
        g_free(trabalho->senha);
    }
    if (trabalho->resumo) {
        sodium_memzero(trabalho->resumo, strlen(trabalho->resumo));
        g_free(trabalho->resumo);
    }
    g_free(trabalho);
}

static void executar_trabalho(GTask *tarefa, gpointer origem,
                              gpointer dados, GCancellable *cancelamento) {
    trabalho_t *trabalho = (trabalho_t *)dados;
    resultado_t *resultado = g_new0(resultado_t, 1);
    int retorno;

    (void)origem;
    (void)cancelamento;

    if (trabalho->tipo == TRABALHO_PROTEGER_SENHA) {
        retorno = crypto_pwhash_str_alg(
            resultado->resumo,
            (const char *)trabalho->senha,
            (unsigned long long)trabalho->senha_tamanho,
            SEGREDO_ITERACOES,
            SEGREDO_MEMORIA,
            crypto_pwhash_ALG_ARGON2ID13
        );
        if (retorno == 0) {
            resultado->sucesso = TRUE;
        } else {
            resultado->falha = g_strdup(
                "não foi possível proteger a senha (memória insuficiente)"
            );
        }
    } else {
        retorno = crypto_pwhash_str_verify(
            trabalho->resumo,
            (const char *)trabalho->senha,
            (unsigned long long)trabalho->senha_tamanho
        );
        resultado->sucesso = TRUE;
        resultado->confere = (retorno == 0);
    }

    g_task_return_pointer(tarefa, resultado, liberar_resultado);
}

static void concluir_trabalho(GObject *origem, GAsyncResult *retorno,
                              gpointer dados) {
    trabalho_t *trabalho = (trabalho_t *)dados;
    lua_State *L = trabalho->L;
    resultado_t *resultado;
    GError *erro = NULL;

    (void)origem;

    resultado = (resultado_t *)g_task_propagate_pointer(
        G_TASK(retorno), &erro
    );

    lua_rawgeti(L, LUA_REGISTRYINDEX, trabalho->tratador_ref);

    if (!resultado || erro) {
        lua_pushnil(L);
        lua_pushstring(L, erro ? erro->message : "falha interna ao tratar senha");
    } else if (!resultado->sucesso) {
        lua_pushnil(L);
        lua_pushstring(L, resultado->falha ? resultado->falha :
                       "falha interna ao tratar senha");
    } else if (trabalho->tipo == TRABALHO_PROTEGER_SENHA) {
        lua_pushstring(L, resultado->resumo);
        lua_pushnil(L);
    } else {
        lua_pushboolean(L, resultado->confere);
        lua_pushnil(L);
    }

    lua_rawgeti(L, LUA_REGISTRYINDEX, trabalho->dado_ref);
    if (lua_pcall(L, 3, 0, 0) != LUA_OK) {
        fprintf(stderr, "[segredo] falha no tratador: %s\n",
                lua_tostring(L, -1));
        lua_pop(L, 1);
    }

    luaL_unref(L, LUA_REGISTRYINDEX, trabalho->tratador_ref);
    luaL_unref(L, LUA_REGISTRYINDEX, trabalho->dado_ref);
    if (erro) g_error_free(erro);
    if (resultado) liberar_resultado(resultado);
    liberar_trabalho(trabalho);
}

static int iniciar_trabalho(lua_State *L, tipo_trabalho_t tipo) {
    size_t senha_tamanho;
    const char *senha;
    const char *resumo = NULL;
    int índice_tratador;
    int índice_dado;
    trabalho_t *trabalho;
    GTask *tarefa;

    if (tipo == TRABALHO_PROTEGER_SENHA) {
        senha = luaL_checklstring(L, 1, &senha_tamanho);
        índice_tratador = 2;
        índice_dado = 3;
    } else {
        resumo = luaL_checkstring(L, 1);
        senha = luaL_checklstring(L, 2, &senha_tamanho);
        índice_tratador = 3;
        índice_dado = 4;
    }

    luaL_checktype(L, índice_tratador, LUA_TFUNCTION);
    if (senha_tamanho == 0 || senha_tamanho > 1024) {
        return luaL_error(L, "senha deve ter entre 1 e 1024 tacos");
    }

    trabalho = g_new0(trabalho_t, 1);
    trabalho->L = L;
    trabalho->tipo = tipo;
    trabalho->senha = g_memdup2(senha, senha_tamanho);
    trabalho->senha_tamanho = senha_tamanho;
    if (resumo) trabalho->resumo = g_strdup(resumo);

    lua_pushvalue(L, índice_tratador);
    trabalho->tratador_ref = luaL_ref(L, LUA_REGISTRYINDEX);
    if (lua_gettop(L) >= índice_dado) lua_pushvalue(L, índice_dado);
    else lua_pushnil(L);
    trabalho->dado_ref = luaL_ref(L, LUA_REGISTRYINDEX);

    tarefa = g_task_new(NULL, NULL, concluir_trabalho, trabalho);
    g_task_set_task_data(tarefa, trabalho, NULL);
    g_task_run_in_thread(tarefa, executar_trabalho);
    g_object_unref(tarefa);

    lua_pushboolean(L, 1);
    return 1;
}

static int l_proteger_senha_async(lua_State *L) {
    return iniciar_trabalho(L, TRABALHO_PROTEGER_SENHA);
}

static int l_conferir_senha_async(lua_State *L) {
    return iniciar_trabalho(L, TRABALHO_CONFERIR_SENHA);
}

static int l_novo_token(lua_State *L) {
    lua_Integer tamanho = luaL_optinteger(L, 1, 32);
    unsigned char *bruto;
    char *codificado;
    size_t codificado_tamanho;

    luaL_argcheck(L, tamanho >= 16 && tamanho <= 64, 1,
                  "tamanho deve ficar entre 16 e 64 tacos");

    bruto = g_malloc((gsize)tamanho);
    randombytes_buf(bruto, (size_t)tamanho);
    codificado_tamanho = sodium_base64_ENCODED_LEN(
        (size_t)tamanho, sodium_base64_VARIANT_URLSAFE_NO_PADDING
    );
    codificado = g_malloc(codificado_tamanho);
    sodium_bin2base64(codificado, codificado_tamanho, bruto,
                      (size_t)tamanho,
                      sodium_base64_VARIANT_URLSAFE_NO_PADDING);
    lua_pushstring(L, codificado);

    sodium_memzero(bruto, (size_t)tamanho);
    g_free(bruto);
    sodium_memzero(codificado, codificado_tamanho);
    g_free(codificado);
    return 1;
}

static int l_resumir_token(lua_State *L) {
    size_t tamanho;
    const unsigned char *texto =
        (const unsigned char *)luaL_checklstring(L, 1, &tamanho);
    unsigned char resumo[SEGREDO_RESUMO_TACOS];
    char hexadecimal[SEGREDO_RESUMO_TACOS * 2 + 1];

    crypto_generichash(resumo, sizeof(resumo), texto,
                       (unsigned long long)tamanho, NULL, 0);
    sodium_bin2hex(hexadecimal, sizeof(hexadecimal), resumo, sizeof(resumo));
    lua_pushstring(L, hexadecimal);
    sodium_memzero(resumo, sizeof(resumo));
    sodium_memzero(hexadecimal, sizeof(hexadecimal));
    return 1;
}

static int l_conferir_token(lua_State *L) {
    size_t tamanho_a, tamanho_b;
    const unsigned char *a =
        (const unsigned char *)luaL_checklstring(L, 1, &tamanho_a);
    const unsigned char *b =
        (const unsigned char *)luaL_checklstring(L, 2, &tamanho_b);

    if (tamanho_a != tamanho_b) {
        lua_pushboolean(L, 0);
        return 1;
    }
    lua_pushboolean(L, sodium_memcmp(a, b, tamanho_a) == 0);
    return 1;
}

static int l_precisa_atualizar(lua_State *L) {
    const char *resumo = luaL_checkstring(L, 1);
    int retorno = crypto_pwhash_str_needs_rehash(
        resumo, SEGREDO_ITERACOES, SEGREDO_MEMORIA
    );
    if (retorno < 0) {
        lua_pushnil(L);
        lua_pushliteral(L, "resumo de senha inválido");
        return 2;
    }
    lua_pushboolean(L, retorno != 0);
    return 1;
}

static const luaL_Reg segredo_funções[] = {
    {"protejaSenhaAss\xC3\xADncrono", l_proteger_senha_async},
    {"confiraSenhaAss\xC3\xADncrono", l_conferir_senha_async},
    {"novoBilhete", l_novo_token},
    {"resumaBilhete", l_resumir_token},
    {"confiraBilhete", l_conferir_token},
    {"precisaAtualizarSenha", l_precisa_atualizar},
    {NULL, NULL}
};

LUA_API int luaopen_segredo(lua_State *L) {
    if (sodium_init() < 0) {
        return luaL_error(L, "não foi possível iniciar a libsodium");
    }
    luaL_newlib(L, segredo_funções);
    lua_pushliteral(L, "Argon2id");
    lua_setfield(L, -2, "algoritmo");
    return 1;
}
