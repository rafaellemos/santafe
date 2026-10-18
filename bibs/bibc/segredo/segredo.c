/*
 * segredo.c
 * Proteção de senhas e bilhetes opacos para Santafé.
 *
 * As senhas usam Argon2id pelo formato autocontido da libsodium. O trabalho
 * deliberadamente caro ocorre numa thread; somente o retorno toca a VM.
 */

#include <gio/gio.h>
#include <sodium.h>
#include <openssl/err.h>
#include <openssl/evp.h>
#include <openssl/pem.h>
#include <openssl/rsa.h>
#include <openssl/x509.h>
#if OPENSSL_VERSION_NUMBER >= 0x30000000L
#include <openssl/core_names.h>
#include <openssl/decoder.h>
#endif
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

static int falha_openssl(lua_State *L, const char *contexto) {
    unsigned long código = ERR_get_error();
    char detalhe[256];

    lua_pushnil(L);
    if (código == 0) {
        lua_pushfstring(L, "%s", contexto);
        return 2;
    }
    ERR_error_string_n(código, detalhe, sizeof(detalhe));
    lua_pushfstring(L, "%s: %s", contexto, detalhe);
    return 2;
}

/* SHA-256 binário. O chamador escolhe hexadecimal ou Base64 conforme o
 * protocolo; DKIM exige Base64 e, portanto, não deve receber hexadecimal. */
static int l_resumir_sha256(lua_State *L) {
    size_t tamanho;
    const unsigned char *dados =
        (const unsigned char *)luaL_checklstring(L, 1, &tamanho);
    unsigned char resumo[crypto_hash_sha256_BYTES];

    crypto_hash_sha256(resumo, dados, (unsigned long long)tamanho);
    lua_pushlstring(L, (const char *)resumo, sizeof(resumo));
    sodium_memzero(resumo, sizeof(resumo));
    return 1;
}

/* Assina os dados com RSA PKCS#1 v1.5 e SHA-256, combinação exigida pelo
 * perfil rsa-sha256 do DKIM. A chave PEM permanece em memória somente
 * durante a chamada e a assinatura é devolvida em formato binário. */
static int l_assinar_rsa_sha256(lua_State *L) {
    size_t dados_tamanho, pem_tamanho;
    const unsigned char *dados =
        (const unsigned char *)luaL_checklstring(L, 1, &dados_tamanho);
    const char *pem = luaL_checklstring(L, 2, &pem_tamanho);
    BIO *bio = NULL;
    EVP_PKEY *chave = NULL;
    EVP_MD_CTX *contexto = NULL;
    unsigned char *assinatura = NULL;
    size_t assinatura_tamanho = 0;
    int retorno;

    luaL_argcheck(L, pem_tamanho > 0 && pem_tamanho <= 1024U * 1024U, 2,
                  "chave RSA PEM deve ter entre 1 taco e 1 MiB");
    ERR_clear_error();
    bio = BIO_new_mem_buf(pem, (int)pem_tamanho);
    if (!bio) return falha_openssl(L, "não foi possível abrir a chave RSA");

    chave = PEM_read_bio_PrivateKey(bio, NULL, NULL, NULL);
    BIO_free(bio);
    if (!chave) return falha_openssl(L, "chave RSA privada inválida");
    if (EVP_PKEY_base_id(chave) != EVP_PKEY_RSA) {
        EVP_PKEY_free(chave);
        lua_pushnil(L);
        lua_pushliteral(L, "a chave privada precisa ser RSA");
        return 2;
    }

    contexto = EVP_MD_CTX_new();
    if (!contexto) {
        EVP_PKEY_free(chave);
        return falha_openssl(L, "não foi possível iniciar a assinatura RSA");
    }
    retorno = EVP_DigestSignInit(contexto, NULL, EVP_sha256(), NULL, chave);
    if (retorno == 1)
        retorno = EVP_DigestSignUpdate(contexto, dados, dados_tamanho);
    if (retorno == 1)
        retorno = EVP_DigestSignFinal(contexto, NULL, &assinatura_tamanho);
    if (retorno != 1 || assinatura_tamanho == 0) {
        EVP_MD_CTX_free(contexto);
        EVP_PKEY_free(chave);
        return falha_openssl(L, "não foi possível calcular a assinatura RSA");
    }

    assinatura = g_malloc(assinatura_tamanho);
    retorno = EVP_DigestSignFinal(contexto, assinatura, &assinatura_tamanho);
    EVP_MD_CTX_free(contexto);
    EVP_PKEY_free(chave);
    if (retorno != 1) {
        sodium_memzero(assinatura, assinatura_tamanho);
        g_free(assinatura);
        return falha_openssl(L, "não foi possível concluir a assinatura RSA");
    }

    lua_pushlstring(L, (const char *)assinatura, assinatura_tamanho);
    sodium_memzero(assinatura, assinatura_tamanho);
    g_free(assinatura);
    return 1;
}

static EVP_PKEY *ler_chave_publica_der(const unsigned char *dados,
                                       size_t tamanho) {
#if OPENSSL_VERSION_NUMBER >= 0x30000000L
    EVP_PKEY *chave = NULL;
    OSSL_DECODER_CTX *decodificador;
    const unsigned char *cursor = dados;
    size_t restante = tamanho;

    decodificador = OSSL_DECODER_CTX_new_for_pkey(
        &chave, "DER", NULL, "RSA", EVP_PKEY_PUBLIC_KEY, NULL, NULL);
    if (!decodificador) return NULL;
    if (OSSL_DECODER_from_data(decodificador, &cursor, &restante) != 1) {
        EVP_PKEY_free(chave);
        chave = NULL;
    }
    OSSL_DECODER_CTX_free(decodificador);
    return chave;
#else
    const unsigned char *cursor = dados;
    EVP_PKEY *chave = d2i_PUBKEY(NULL, &cursor, (long)tamanho);
    if (!chave) {
        RSA *rsa;
        ERR_clear_error();
        cursor = dados;
        rsa = d2i_RSAPublicKey(NULL, &cursor, (long)tamanho);
        if (rsa) {
            chave = EVP_PKEY_new();
            if (!chave || EVP_PKEY_assign_RSA(chave, rsa) != 1) {
                if (chave) EVP_PKEY_free(chave);
                RSA_free(rsa);
                chave = NULL;
            }
        }
    }
    return chave;
#endif
}

/* Confere uma assinatura RSA PKCS#1 v1.5 com SHA-256. A chave pública pode
 * chegar em PEM ou no DER publicado no campo p= de um registro DKIM. Aceitar
 * ambos evita converter material criptográfico em código Santafé. */
static int l_verificar_rsa_sha256(lua_State *L) {
    size_t dados_tamanho, assinatura_tamanho, chave_tamanho;
    const unsigned char *dados =
        (const unsigned char *)luaL_checklstring(L, 1, &dados_tamanho);
    const unsigned char *assinatura =
        (const unsigned char *)luaL_checklstring(L, 2, &assinatura_tamanho);
    const unsigned char *chave_dados =
        (const unsigned char *)luaL_checklstring(L, 3, &chave_tamanho);
    EVP_PKEY *chave = NULL;
    EVP_MD_CTX *contexto = NULL;
    BIO *bio = NULL;
    int retorno;

    luaL_argcheck(L, assinatura_tamanho > 0 && assinatura_tamanho <= 8192U,
                  2, "assinatura RSA deve ter entre 1 taco e 8 KiB");
    luaL_argcheck(L, chave_tamanho > 0 && chave_tamanho <= 1024U * 1024U,
                  3, "chave RSA deve ter entre 1 taco e 1 MiB");

    ERR_clear_error();
    if (chave_tamanho >= 10U &&
        memcmp(chave_dados, "-----BEGIN", 10U) == 0) {
        bio = BIO_new_mem_buf(chave_dados, (int)chave_tamanho);
        if (!bio) return falha_openssl(L, "não foi possível abrir a chave RSA");
        chave = PEM_read_bio_PUBKEY(bio, NULL, NULL, NULL);
        BIO_free(bio);
    } else {
        chave = ler_chave_publica_der(chave_dados, chave_tamanho);
    }
    if (!chave) return falha_openssl(L, "chave pública RSA inválida");
    if (EVP_PKEY_base_id(chave) != EVP_PKEY_RSA) {
        EVP_PKEY_free(chave);
        lua_pushnil(L);
        lua_pushliteral(L, "a chave pública precisa ser RSA");
        return 2;
    }
    if (EVP_PKEY_bits(chave) < 1024) {
        EVP_PKEY_free(chave);
        lua_pushnil(L);
        lua_pushliteral(L, "a chave pública RSA possui menos de 1024 ticos");
        return 2;
    }

    contexto = EVP_MD_CTX_new();
    if (!contexto) {
        EVP_PKEY_free(chave);
        return falha_openssl(L, "não foi possível iniciar a verificação RSA");
    }
    retorno = EVP_DigestVerifyInit(contexto, NULL, EVP_sha256(), NULL, chave);
    if (retorno == 1)
        retorno = EVP_DigestVerifyUpdate(contexto, dados, dados_tamanho);
    if (retorno == 1)
        retorno = EVP_DigestVerifyFinal(contexto, assinatura,
                                        assinatura_tamanho);
    EVP_MD_CTX_free(contexto);
    EVP_PKEY_free(chave);

    if (retorno == 1) {
        lua_pushboolean(L, 1);
        return 1;
    }
    if (retorno == 0) {
        ERR_clear_error();
        lua_pushboolean(L, 0);
        return 1;
    }
    return falha_openssl(L, "não foi possível conferir a assinatura RSA");
}

/* Converte uma chave RSA PEM (privada ou pública) para o campo Public Key de
 * um DNSKEY RSASHA256, conforme a RFC 3110: comprimento do expoente,
 * expoente e módulo, todos em ordem de rede. Não devolve o invólucro DER. */
static int l_chave_publica_rsa(lua_State *L) {
    size_t pem_tamanho;
    const char *pem = luaL_checklstring(L, 1, &pem_tamanho);
    BIO *bio = NULL;
    EVP_PKEY *chave = NULL;
    BIGNUM *módulo = NULL;
    BIGNUM *expoente = NULL;
    unsigned char *resultado = NULL;
    size_t tamanho_do_expoente, tamanho_do_módulo, cabeçalho, total;

    luaL_argcheck(L, pem_tamanho > 0 && pem_tamanho <= 1024U * 1024U, 1,
                  "chave RSA PEM deve ter entre 1 taco e 1 MiB");
    ERR_clear_error();
    bio = BIO_new_mem_buf(pem, (int)pem_tamanho);
    if (!bio) return falha_openssl(L, "não foi possível abrir a chave RSA");
    chave = PEM_read_bio_PrivateKey(bio, NULL, NULL, NULL);
    BIO_free(bio);

    if (!chave) {
        ERR_clear_error();
        bio = BIO_new_mem_buf(pem, (int)pem_tamanho);
        if (!bio) return falha_openssl(L, "não foi possível abrir a chave RSA");
        chave = PEM_read_bio_PUBKEY(bio, NULL, NULL, NULL);
        BIO_free(bio);
    }
    if (!chave) return falha_openssl(L, "chave RSA PEM inválida");
    if (EVP_PKEY_base_id(chave) != EVP_PKEY_RSA) {
        EVP_PKEY_free(chave);
        lua_pushnil(L);
        lua_pushliteral(L, "a chave precisa ser RSA");
        return 2;
    }

#if OPENSSL_VERSION_NUMBER >= 0x30000000L
    if (EVP_PKEY_get_bn_param(chave, OSSL_PKEY_PARAM_RSA_N, &módulo) != 1 ||
        EVP_PKEY_get_bn_param(chave, OSSL_PKEY_PARAM_RSA_E, &expoente) != 1) {
        EVP_PKEY_free(chave);
        BN_free(módulo);
        BN_free(expoente);
        return falha_openssl(L, "não foi possível ler a chave pública RSA");
    }
#else
    {
        RSA *rsa = EVP_PKEY_get1_RSA(chave);
        const BIGNUM *n = NULL;
        const BIGNUM *e = NULL;
        if (!rsa) {
            EVP_PKEY_free(chave);
            return falha_openssl(L, "não foi possível ler a chave pública RSA");
        }
        RSA_get0_key(rsa, &n, &e, NULL);
        módulo = BN_dup(n);
        expoente = BN_dup(e);
        RSA_free(rsa);
        if (!módulo || !expoente) {
            EVP_PKEY_free(chave);
            BN_free(módulo);
            BN_free(expoente);
            return falha_openssl(L, "não foi possível copiar a chave pública RSA");
        }
    }
#endif
    EVP_PKEY_free(chave);

    tamanho_do_expoente = (size_t)BN_num_bytes(expoente);
    tamanho_do_módulo = (size_t)BN_num_bytes(módulo);
    if (tamanho_do_expoente == 0 || tamanho_do_expoente > 65535U ||
        tamanho_do_módulo < 128U || tamanho_do_módulo > 8192U) {
        BN_free(módulo);
        BN_free(expoente);
        lua_pushnil(L);
        lua_pushliteral(L, "dimensões da chave pública RSA inválidas para DNSKEY");
        return 2;
    }

    cabeçalho = tamanho_do_expoente < 256U ? 1U : 3U;
    total = cabeçalho + tamanho_do_expoente + tamanho_do_módulo;
    resultado = g_malloc(total);
    if (cabeçalho == 1U) {
        resultado[0] = (unsigned char)tamanho_do_expoente;
    } else {
        resultado[0] = 0;
        resultado[1] = (unsigned char)(tamanho_do_expoente >> 8);
        resultado[2] = (unsigned char)tamanho_do_expoente;
    }
    BN_bn2bin(expoente, resultado + cabeçalho);
    BN_bn2bin(módulo, resultado + cabeçalho + tamanho_do_expoente);
    BN_free(módulo);
    BN_free(expoente);

    lua_pushlstring(L, (const char *)resultado, total);
    g_free(resultado);
    return 1;
}

static const luaL_Reg segredo_funções[] = {
    {"protejaSenhaAss\xC3\xADncrono", l_proteger_senha_async},
    {"confiraSenhaAss\xC3\xADncrono", l_conferir_senha_async},
    {"novoBilhete", l_novo_token},
    {"resuma", l_resumir_token},
    {"resumaBilhete", l_resumir_token},
    {"confiraBilhete", l_conferir_token},
    {"precisaAtualizarSenha", l_precisa_atualizar},
    {"resumaSHA256", l_resumir_sha256},
    {"assineRSA256", l_assinar_rsa_sha256},
    {"verifiqueRSA256", l_verificar_rsa_sha256},
    {"chaveP\xC3\xBA" "blicaRSA", l_chave_publica_rsa},
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
