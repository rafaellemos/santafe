/**
 * rede.c
 * Santafé rede async (GIO) — Modo "Full Async" (corrigido e escapado)
 *
 * - Corrigido: mensagens g_printerr com terminação
 * - Corrigido: g_socket_set_option uso correto
 * - Corrigido: manipulação segura da pilha Lua nas callbacks (sem índices negativos)
 * - Corrigido: unref seguro e limpeza de buffers
 * - Ajustado: Literais de string escapados para UTF-8 Hexadecimal
 *
 * Baseado no arquivo original enviado pelo usuário.
 */

#define _GNU_SOURCE
#include <gio/gio.h>
#include <glib.h>
#include <string.h>
#include <stdlib.h>
#include <errno.h>
#ifdef _WIN32
#include <winsock2.h>
#else
#include <sys/socket.h>
#include <netinet/in.h>
#endif

#include "lua.h"
#include "lualib.h"
#include "lauxlib.h"

/* G_SOURCE_FUNC existe no GLib >= 2.58. Mantém a mesma conversão segura
 * para distribuições Linux com GLib anterior, sem avisos de protótipo. */
#ifndef G_SOURCE_FUNC
#define G_SOURCE_FUNC(f) ((GSourceFunc)(void (*)(void))(f))
#endif

/* Adaptadores para API padrão Lua (substituem macros específicas da VM Santafé) */
#define p_pushtrue(L)         lua_pushboolean((L), 1)
#define p_pushnil(L)          lua_pushnil(L)
#define p_getstring(L, i)     luaL_checkstring((L), (i))
#define p_getlstring(L, i, l) luaL_checklstring((L), (i), (l))
#define p_pushinteger(L, n)   lua_pushinteger((L), (lua_Integer)(n))
#define p_pushstring(L, s)    lua_pushstring((L), (s))


#ifndef LUA_NOREF
#define LUA_NOREF -2
#endif

/* ---------------- types ---------------- */
/* ---------- Helpers simples de HTTP / string ---------- */

static const char *find_crlf(const char *s, const char *end) {
    for (const char *p = s; p < end; p++) {
        if (*p == '\r') {
            if (p + 1 < end && p[1] == '\n') return p;
        } else if (*p == '\n') {
            return p;
        }
    }
    return NULL;
}
/* ---------- Helpers HTTP para resposta ---------- */

static const char* http_reason_phrase(int status) {
    switch (status) {
        case 200: return "OK";
        case 201: return "Criado"; /* Created */
        case 202: return "Aceito"; /* Accepted */
        case 204: return "Sem Conte\xC3\xBA" "do"; /* No Content */
        case 301: return "Movido Permanentemente"; /* Moved Permanently */
        case 302: return "Encontrado"; /* Found */
        case 400: return "Requisi\xC3\xA7\xC3\xA3o Inv\xC3\xA1lida"; /* Bad Request */
        case 401: return "N\xC3\xA3o Autorizado"; /* Unauthorized */
        case 403: return "Proibido"; /* Forbidden */
        case 404: return "N\xC3\xA3o Encontrado"; /* Not Found */
        case 405: return "M\xC3\xA9todo N\xC3\xA3o Permitido"; /* Method Not Allowed */
        case 413: return "Carga Muito Grande"; /* Payload Too Large */
        case 500: return "Erro Interno do Servidor"; /* Internal Server Error */
        case 502: return "Gateway Ruim"; /* Bad Gateway */
        case 503: return "Servi\xC3\xA7o Indispon\xC3\xADvel"; /* Service Unavailable */
        default:  return "OK";
    }
}

/* trim left/right espaços e tabs; retorna novo início e novo fim (end é exclusívo) */
static void trim_ascii(const char **start, const char **end) {
    const char *s = *start;
    const char *e = *end;

    while (s < e && (*s == ' ' || *s == '\t')) s++;
    while (e > s && (e[-1] == ' ' || e[-1] == '\t' || e[-1] == '\r' || e[-1] == '\n')) e--;

    *start = s;
    *end = e;
}

/* coloca header name em minúsculas (para chave da tabela headers) */
static void lowercase_ascii(char *s) {
    for (; *s; s++) {
        if (*s >= 'A' && *s <= 'Z') *s = (char)(*s - 'A' + 'a');
    }
}

static int hex_value(unsigned char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

static gboolean push_url_decoded(lua_State *L, const char *text, size_t len,
                                 const char **message) {
    GString *decoded = g_string_sized_new(len);
    for (size_t i = 0; i < len; i++) {
        unsigned char c = (unsigned char)text[i];
        if (c == '+') {
            g_string_append_c(decoded, ' ');
        } else if (c == '%') {
            if (i + 2 >= len) {
                g_string_free(decoded, TRUE);
                *message = "escape percentual incompleto na consulta";
                return FALSE;
            }
            int hi = hex_value((unsigned char)text[i + 1]);
            int lo = hex_value((unsigned char)text[i + 2]);
            if (hi < 0 || lo < 0) {
                g_string_free(decoded, TRUE);
                *message = "escape percentual inv\xC3\xA1lido na consulta";
                return FALSE;
            }
            g_string_append_c(decoded, (char)((hi << 4) | lo));
            i += 2;
        } else {
            g_string_append_c(decoded, (char)c);
        }
    }
    lua_pushlstring(L, decoded->str, decoded->len);
    g_string_free(decoded, TRUE);
    return TRUE;
}

/* parseia e decodifica querystring "a=1&b=2" em tabela Lua (no topo). */
static gboolean parse_query_string(lua_State *L, const char *qs, size_t len,
                                   const char **message) {
    const char *p = qs;
    const char *end = qs + len;

    while (p < end) {
        const char *key_start = p;
        const char *key_end = NULL;
        const char *val_start = NULL;
        const char *val_end = NULL;

        /* encontra '=' ou '&' ou fim */
        for (; p < end && *p != '&' && *p != '='; p++);

        if (p < end && *p == '=') {
            key_end = p;
            p++; /* pula '=' */
            val_start = p;
            for (; p < end && *p != '&'; p++);
            val_end = p;
        } else {
            key_end = p;
            val_start = val_end = NULL;
        }

        if (key_end > key_start) {
            if (!push_url_decoded(L, key_start, (size_t)(key_end - key_start), message))
                return FALSE;

            if (val_start && val_end > val_start) {
                if (!push_url_decoded(L, val_start, (size_t)(val_end - val_start), message)) {
                    lua_pop(L, 1); /* chave */
                    return FALSE;
                }
            } else {
                lua_pushstring(L, "");
            }

            lua_settable(L, -3); /* query[chave] = valor */
        }

        if (p < end && *p == '&') p++;
    }
    return TRUE;
}

typedef struct {
    GSocketConnection *conn;
    GInputStream *istream;
    GOutputStream *ostream;
    gboolean closed;
    gboolean read_pending;
    gboolean write_pending;
    GCancellable *read_cancel;
    GCancellable *write_cancel;
    guint timeout_ms;
    gsize max_header_bytes;
    gsize max_body_bytes;
} psock_conn_t;

typedef struct {
    GSocketClient *client;
    gboolean closed;
    gboolean connect_pending;
    GCancellable *connect_cancel;
    guint timeout_ms;
    gboolean validate_tls;
} psock_client_t;

typedef struct {
    GSocketListener *listener;
    gboolean closed;
    gboolean accept_pending;
    GCancellable *accept_cancel;
    guint timeout_ms;
} psock_server_t;

typedef struct {
    GSocket *socket;
    gboolean closed;
    guint recv_source_id;
    int recv_ref;
    gboolean send_pending;
    guint send_source_id;
    guint send_timeout_id;
    GCancellable *send_cancel;
    guint timeout_ms;
} psock_udp_t;
/* ---------------- Http Response Object ---------------- */

typedef struct {
    psock_conn_t *conn;
    int status;
    GHashTable *headers;
} psock_res_t;

typedef struct {
    int ref;           /* registry index for { func = ..., dado = ... } */
    int self_ref;      /* registry index for 'self' object */
    lua_State *L;
    gpointer buffer;
    gsize buflen;
    GByteArray *accum;
    GCancellable *cancellable;
    guint timeout_id;
    gboolean timed_out;
    psock_conn_t *conn_owner;
    psock_client_t *client_owner;
    psock_server_t *server_owner;
    gboolean parse_http;
    gsize max_total;
} async_ctx_t;

typedef struct {
    int ref;
    lua_State *L;
    GSocket *socket;
    gsize maxlen;
    gpointer buffer;
    guint source_id;
    psock_udp_t *owner;
} udp_recv_state_t;

typedef struct {
    async_ctx_t *ctx;
    psock_udp_t *owner;
    GSocketAddress *dest;
    guint source_id;
} udp_send_state_t;

static GMainLoop *rede_main_loop = NULL;

#define REDE_HTTP_HEADER_PADRAO (32u * 1024u)
#define REDE_HTTP_CORPO_PADRAO  (8u * 1024u * 1024u)
#define REDE_HTTP_CHUNK         (8u * 1024u)
#define REDE_LEITURA_CRUA_MAX   (64u * 1024u * 1024u)


/* ---------------- helpers ---------------- */

static int push_nil_err(lua_State *L, const char *msg) {
    p_pushnil(L);
    p_pushstring(L, msg ? msg : "erro");
    return 2;
}

static int check_port(lua_State *L, int idx, gboolean allow_zero) {
    lua_Integer value = luaL_checkinteger(L, idx);
    lua_Integer minimum = allow_zero ? 0 : 1;
    luaL_argcheck(L, value >= minimum && value <= 65535, idx,
                  allow_zero ? "porta fora do intervalo 0..65535" :
                               "porta fora do intervalo 1..65535");
    return (int)value;
}

static int l_rede_analiseHTTP(lua_State *L);

static const char *gio_error_message(GError *err, const char *fallback) {
    if (!err) return fallback;
    if (err->domain == G_IO_ERROR) {
        switch (err->code) {
            case G_IO_ERROR_CANCELLED: return "opera\xC3\xA7\xC3\xA3o cancelada";
            case G_IO_ERROR_TIMED_OUT: return "tempo limite excedido";
            case G_IO_ERROR_PERMISSION_DENIED: return "permiss\xC3\xA3o negada";
            case G_IO_ERROR_CLOSED: return "conector fechado";
            case G_IO_ERROR_WOULD_BLOCK: return "opera\xC3\xA7\xC3\xA3o bloquearia";
            case G_IO_ERROR_HOST_NOT_FOUND: return "hospedeiro n\xC3\xA3o encontrado";
            case G_IO_ERROR_ADDRESS_IN_USE: return "endere\xC3\xA7o j\xC3\xA1 est\xC3\xA1 em uso";
            case G_IO_ERROR_HOST_UNREACHABLE: return "hospedeiro inalcan\xC3\xA7\xC3\xA1vel";
            case G_IO_ERROR_NETWORK_UNREACHABLE: return "rede inalcan\xC3\xA7\xC3\xA1vel";
            case G_IO_ERROR_CONNECTION_REFUSED: return "conex\xC3\xA3o recusada";
            case G_IO_ERROR_BROKEN_PIPE: return "conex\xC3\xA3o fechada pelo outro lado";
            case G_IO_ERROR_NOT_CONNECTED: return "conector n\xC3\xA3o conectado";
            default: break;
        }
    }
    return err->message ? err->message : fallback;
}

static const char *async_error_message(async_ctx_t *ctx, GError *err,
                                       const char *fallback) {
    if (ctx && ctx->timed_out) return "tempo limite excedido";
    if (err && g_error_matches(err, G_IO_ERROR, G_IO_ERROR_CANCELLED))
        return "opera\xC3\xA7\xC3\xA3o cancelada";
    return gio_error_message(err, fallback);
}

static gboolean async_timeout_cb(gpointer user_data) {
    async_ctx_t *ctx = (async_ctx_t*)user_data;
    if (!ctx) return G_SOURCE_REMOVE;
    ctx->timeout_id = 0;
    ctx->timed_out = TRUE;
    if (ctx->cancellable) g_cancellable_cancel(ctx->cancellable);
    return G_SOURCE_REMOVE;
}

static void arm_async_timeout(async_ctx_t *ctx, guint timeout_ms) {
    if (!ctx || timeout_ms == 0) return;
    ctx->timeout_id = g_timeout_add(timeout_ms, async_timeout_cb, ctx);
}

static void clear_conn_read(async_ctx_t *ctx) {
    if (!ctx || !ctx->conn_owner) return;
    ctx->conn_owner->read_pending = FALSE;
    if (ctx->conn_owner->read_cancel == ctx->cancellable)
        ctx->conn_owner->read_cancel = NULL;
}

static void clear_conn_write(async_ctx_t *ctx) {
    if (!ctx || !ctx->conn_owner) return;
    ctx->conn_owner->write_pending = FALSE;
    if (ctx->conn_owner->write_cancel == ctx->cancellable)
        ctx->conn_owner->write_cancel = NULL;
}

static void clear_client_connect(async_ctx_t *ctx) {
    if (!ctx || !ctx->client_owner) return;
    ctx->client_owner->connect_pending = FALSE;
    if (ctx->client_owner->connect_cancel == ctx->cancellable)
        ctx->client_owner->connect_cancel = NULL;
}

static void clear_server_accept(async_ctx_t *ctx) {
    if (!ctx || !ctx->server_owner) return;
    ctx->server_owner->accept_pending = FALSE;
    if (ctx->server_owner->accept_cancel == ctx->cancellable)
        ctx->server_owner->accept_cancel = NULL;
}

/* store_callback: cria uma tabela { func = <func>, dado = <dado> } e retorna ref */
static int store_callback(lua_State *L, int func_idx, int dado_idx) {
    lua_newtable(L);                      /* table */
    lua_pushvalue(L, func_idx);           /* table, func */
    lua_setfield(L, -2, "func");          /* table.func = func; stack: table */

    if (lua_isnoneornil(L, dado_idx)) {
        lua_pushnil(L);
    } else {
        lua_pushvalue(L, dado_idx);
    }
    lua_setfield(L, -2, "dado");          /* table.dado = dado */

    return luaL_ref(L, LUA_REGISTRYINDEX); /* pops table and returns ref */
}

/* create_async_ctx: guarda self (idx 1) e callback table (func_idx, dado_idx) */
static async_ctx_t* create_async_ctx(lua_State *L, int func_idx, int dado_idx) {
    async_ctx_t *ctx = g_new0(async_ctx_t, 1);
    ctx->L = L;
    /* store self (index 1) */
    lua_pushvalue(L, 1);
    ctx->self_ref = luaL_ref(L, LUA_REGISTRYINDEX);
    ctx->ref = store_callback(L, func_idx, dado_idx);
    ctx->buffer = NULL;
    ctx->buflen = 0;
    ctx->accum = NULL;
    ctx->cancellable = g_cancellable_new();
    ctx->timeout_id = 0;
    ctx->timed_out = FALSE;
    return ctx;
}

static void free_async_ctx(async_ctx_t *ctx) {
    if (!ctx) return;
    if (ctx->timeout_id > 0) {
        g_source_remove(ctx->timeout_id);
        ctx->timeout_id = 0;
    }
    if (ctx->L) {
        if (ctx->self_ref != LUA_NOREF) {
            luaL_unref(ctx->L, LUA_REGISTRYINDEX, ctx->self_ref);
            ctx->self_ref = LUA_NOREF;
        }
        if (ctx->ref != LUA_NOREF) {
            luaL_unref(ctx->L, LUA_REGISTRYINDEX, ctx->ref);
            ctx->ref = LUA_NOREF;
        }
    }
    if (ctx->buffer) g_free(ctx->buffer);
    if (ctx->accum) g_byte_array_unref(ctx->accum);
    if (ctx->cancellable) g_object_unref(ctx->cancellable);
    g_free(ctx);
}

/* udp state destroy */
static void udp_state_destroy_notify(gpointer user_data) {
    udp_recv_state_t *st = (udp_recv_state_t*) user_data;
    if (!st) return;
    if (st->owner) {
        st->owner->recv_source_id = 0;
        st->owner->recv_ref = LUA_NOREF;
    }
    if (st->L && st->ref != LUA_NOREF) {
        luaL_unref(st->L, LUA_REGISTRYINDEX, st->ref);
        st->ref = LUA_NOREF;
    }
    if (st->socket) { g_object_unref(st->socket); st->socket = NULL; }
    if (st->buffer) { g_free(st->buffer); st->buffer = NULL; }
    g_free(st);
}

/* ---------------- RES METHODS ---------------- */

static guint header_hash_ci(gconstpointer key) {
    const unsigned char *p = (const unsigned char*)key;
    guint hash = 5381;
    while (*p) hash = ((hash << 5) + hash) + (guint)g_ascii_tolower(*p++);
    return hash;
}

static gboolean header_equal_ci(gconstpointer a, gconstpointer b) {
    return g_ascii_strcasecmp((const char*)a, (const char*)b) == 0;
}

static gboolean header_name_valid(const char *name, size_t len) {
    if (len == 0 || memchr(name, '\0', len)) return FALSE;
    for (size_t i = 0; i < len; i++) {
        unsigned char c = (unsigned char)name[i];
        if (g_ascii_isalnum(c)) continue;
        if (!strchr("!#$%&'*+-.^_`|~", c)) return FALSE;
    }
    return TRUE;
}

static gboolean header_value_valid(const char *value, size_t len) {
    for (size_t i = 0; i < len; i++) {
        unsigned char c = (unsigned char)value[i];
        if (c == '\t') continue;
        if (c < 0x20 || c == 0x7f) return FALSE;
    }
    return TRUE;
}

static gboolean protected_response_header(const char *name) {
    return g_ascii_strcasecmp(name, "Content-Length") == 0 ||
           g_ascii_strcasecmp(name, "Connection") == 0 ||
           g_ascii_strcasecmp(name, "Transfer-Encoding") == 0;
}

static int l_res_status(lua_State *L) {
    psock_res_t *r = luaL_checkudata(L, 1, "rede{res}");
    lua_Integer st = luaL_checkinteger(L, 2);
    if (st < 100 || st > 599) return push_nil_err(L, "c\xC3\xB3" "digo HTTP fora do intervalo 100..599");
    r->status = (int)st;
    lua_settop(L, 1);
    return 1;
}

static int l_res_set_header(lua_State *L) {
    psock_res_t *r = luaL_checkudata(L, 1, "rede{res}");
    size_t nome_len = 0, valor_len = 0;
    const char *nome = luaL_checklstring(L, 2, &nome_len);
    const char *valor = luaL_checklstring(L, 3, &valor_len);
    if (!header_name_valid(nome, nome_len)) return push_nil_err(L, "nome de cabe\xC3\xA7" "alho inv\xC3\xA1lido");
    if (!header_value_valid(valor, valor_len)) return push_nil_err(L, "valor de cabe\xC3\xA7" "alho inv\xC3\xA1lido");
    if (protected_response_header(nome))
        return push_nil_err(L, "esse cabe\xC3\xA7" "alho \xC3\xA9 controlado pela biblioteca");
    g_hash_table_replace(r->headers, g_strdup(nome), g_strdup(valor));
    lua_settop(L, 1);
    return 1;
}

static int l_res_enviar(lua_State *L) {
    psock_res_t *r = luaL_checkudata(L, 1, "rede{res}");

    size_t len = 0;
    const char *body = p_getlstring(L, 2, &len);
    const char *reason = http_reason_phrase(r->status);

    GString *g = g_string_sized_new(len + 256);

    g_string_append_printf(g, "HTTP/1.1 %d %s\r\n", r->status, reason);

    // Headers
    GHashTableIter iter;
    gpointer k, v;
    g_hash_table_iter_init(&iter, r->headers);

    while (g_hash_table_iter_next(&iter, &k, &v)) {
        g_string_append_printf(g, "%s: %s\r\n", (char*)k, (char*)v);
    }

    g_string_append_printf(g, "Content-Length: %zu\r\n", len);
    g_string_append(g, "Connection: close\r\n");
    g_string_append(g, "\r\n");

    if (len > 0)
        g_string_append_len(g, body, len);

    lua_pushlstring(L, g->str, g->len);
    g_string_free(g, TRUE);

    return 1;
}

static int l_res_html(lua_State *L) {
    psock_res_t *r = luaL_checkudata(L, 1, "rede{res}");
    g_hash_table_replace(r->headers,
        g_strdup("Content-Type"), g_strdup("text/html; charset=utf-8"));
    return l_res_enviar(L);
}

static int l_res_texto(lua_State *L) {
    psock_res_t *r = luaL_checkudata(L, 1, "rede{res}");
    g_hash_table_replace(r->headers,
        g_strdup("Content-Type"), g_strdup("text/plain; charset=utf-8"));
    return l_res_enviar(L);
}

static int l_res_json(lua_State *L) {
    psock_res_t *r = luaL_checkudata(L, 1, "rede{res}");
    g_hash_table_replace(r->headers,
        g_strdup("Content-Type"), g_strdup("application/json"));
    return l_res_enviar(L);
}

static int l_res_gc(lua_State *L) {
    psock_res_t *r = (psock_res_t*)luaL_checkudata(L, 1, "rede{res}");
    if (r && r->headers) {
        g_hash_table_destroy(r->headers);
        r->headers = NULL;
    }
    r->conn = NULL;
    return 0;
}

/* ---------------- Construtores / Checkers / GCs ---------------- */

static psock_conn_t* push_new_pconn(lua_State *L) {
    psock_conn_t *c = (psock_conn_t*) lua_newuserdata(L, sizeof(psock_conn_t));
    memset(c, 0, sizeof(*c));
    c->timeout_ms = 0;
    c->max_header_bytes = REDE_HTTP_HEADER_PADRAO;
    c->max_body_bytes = REDE_HTTP_CORPO_PADRAO;
    /* rede{conexão} */
    luaL_getmetatable(L, "rede{conex\xC3\xA3o}");
    lua_setmetatable(L, -2);
    return c;
}
static psock_conn_t* check_pconn(lua_State *L, int idx) {
    /* rede{conexão} */
    return (psock_conn_t*) luaL_checkudata(L, idx, "rede{conex\xC3\xA3o}");
}
static psock_client_t* check_pclient(lua_State *L, int idx) {
    /* rede{cliente} */
    return (psock_client_t*) luaL_checkudata(L, idx, "rede{cliente}");
}
static psock_server_t* check_pserver(lua_State *L, int idx) {
    /* rede{servidor} */
    return (psock_server_t*) luaL_checkudata(L, idx, "rede{servidor}");
}
static psock_udp_t* check_pudp(lua_State *L, int idx) {
    /* rede{udp} */
    return (psock_udp_t*) luaL_checkudata(L, idx, "rede{udp}");
}

/* connection close / gc */
static void close_pconn(psock_conn_t *c) {
    if (!c || c->closed) return;
    c->closed = TRUE;
    if (c->read_cancel) g_cancellable_cancel(c->read_cancel);
    if (c->write_cancel) g_cancellable_cancel(c->write_cancel);
    if (c->conn) {
        GError *err = NULL;
        g_io_stream_close(G_IO_STREAM(c->conn), NULL, &err);
        if (err) g_clear_error(&err);
        g_object_unref(c->conn);
        c->conn = NULL;
    }
    c->istream = NULL;
    c->ostream = NULL;
}

static int l_conn_close(lua_State *L) {
    psock_conn_t *c = check_pconn(L, 1);
    close_pconn(c);
    p_pushtrue(L);
    return 1;
}
static int l_conn_gc(lua_State *L) {
    /* rede{conexão} */
    psock_conn_t *c = (psock_conn_t*) luaL_checkudata(L, 1, "rede{conex\xC3\xA3o}");
    close_pconn(c);
    return 0;
}

/* client close / gc */
static void close_pclient(psock_client_t *c) {
    if (!c || c->closed) return;
    c->closed = TRUE;
    if (c->connect_cancel) g_cancellable_cancel(c->connect_cancel);
    if (c->client) g_object_unref(c->client);
    c->client = NULL;
}

static int l_client_close(lua_State *L) {
    psock_client_t *c = check_pclient(L, 1);
    close_pclient(c);
    p_pushtrue(L); return 1;
}
static int l_client_gc(lua_State *L) {
    /* rede{cliente} */
    psock_client_t *c = (psock_client_t*) luaL_checkudata(L, 1, "rede{cliente}");
    close_pclient(c);
    return 0;
}

/* server close / gc */
static void close_pserver(psock_server_t *s) {
    if (!s || s->closed) return;
    s->closed = TRUE;
    if (s->accept_cancel) g_cancellable_cancel(s->accept_cancel);
    if (s->listener) {
        g_socket_listener_close(s->listener);
        g_object_unref(s->listener);
        s->listener = NULL;
    }
}

static int l_server_close(lua_State *L) {
    psock_server_t *s = check_pserver(L, 1);
    close_pserver(s);
    p_pushtrue(L); return 1;
}
static int l_server_gc(lua_State *L) {
    /* rede{servidor} */
    psock_server_t *s = (psock_server_t*) luaL_checkudata(L, 1, "rede{servidor}");
    close_pserver(s);
    return 0;
}

/* constructors */
static gboolean accept_invalid_certificate_cb(GTlsConnection *connection,
                                              GTlsCertificate *peer_cert,
                                              GTlsCertificateFlags errors,
                                              gpointer user_data) {
    (void)connection;
    (void)peer_cert;
    (void)errors;
    (void)user_data;
    return TRUE;
}

static void socket_client_event_cb(GSocketClient *client,
                                   GSocketClientEvent event,
                                   GSocketConnectable *connectable,
                                   GIOStream *connection,
                                   gpointer user_data) {
    (void)client;
    (void)connectable;
    psock_client_t *c = (psock_client_t*)user_data;
    if (event == G_SOCKET_CLIENT_TLS_HANDSHAKING && c && !c->validate_tls &&
        connection && G_IS_TLS_CONNECTION(connection)) {
        g_signal_connect(connection, "accept-certificate",
                         G_CALLBACK(accept_invalid_certificate_cb), NULL);
    }
}

static int l_rede_tcp_cliente(lua_State *L) {
    psock_client_t *c = (psock_client_t*) lua_newuserdata(L, sizeof(psock_client_t));
    memset(c, 0, sizeof(*c));
    c->client = g_socket_client_new();
    c->closed = FALSE;
    c->timeout_ms = 0;
    c->validate_tls = TRUE;
    g_signal_connect(c->client, "event", G_CALLBACK(socket_client_event_cb), c);
    /* rede{cliente} */
    luaL_getmetatable(L, "rede{cliente}");
    lua_setmetatable(L, -2);
    return 1;
}
static int l_rede_tcp_servidor(lua_State *L) {
    psock_server_t *s = (psock_server_t*) lua_newuserdata(L, sizeof(psock_server_t));
    memset(s, 0, sizeof(*s));
    s->listener = g_socket_listener_new();
    s->closed = FALSE;
    s->timeout_ms = 0;
    /* rede{servidor} */
    luaL_getmetatable(L, "rede{servidor}");
    lua_setmetatable(L, -2);
    return 1;
}

/* ---------------- helper to call stored callback safely ----------------
   Stack-safe pattern:
     - push function (remove the table after getting the field)
     - push args in order
     - push dado (get again from registry)
     - lua_pcall with nargs
*/


/* ---------------- CLIENTE: connect_async e TLS ---------------- */

static void connect_finish_cb(GObject *source_object, GAsyncResult *res, gpointer user_data) {
    async_ctx_t *ctx = (async_ctx_t*) user_data;
    GSocketClient *client = G_SOCKET_CLIENT(source_object);
    lua_State *L = ctx ? ctx->L : NULL;
    GError *err = NULL;

    GSocketConnection *conn = g_socket_client_connect_finish(client, res, &err);

    clear_client_connect(ctx);

    if (!ctx || !L) {
        if (conn) g_object_unref(conn);
        if (err) g_clear_error(&err);
        free_async_ctx(ctx);
        return;
    }

    /* Prepare stack: we'll push conn_or_nil, err_or_nil (2 items) before calling helper which will push dado */
    if (ctx->client_owner && ctx->client_owner->closed && conn) {
        g_io_stream_close(G_IO_STREAM(conn), NULL, NULL);
        g_object_unref(conn);
        conn = NULL;
        if (!err) g_set_error_literal(&err, G_IO_ERROR, G_IO_ERROR_CANCELLED,
                                      "cliente fechado");
    }

    if (err || !conn) {
        /* push nil, err_msg */
        lua_rawgeti(L, LUA_REGISTRYINDEX, ctx->ref); /* table */
        lua_getfield(L, -1, "func");                 /* table, func */
        lua_remove(L, -2);                           /* func */
        lua_rawgeti(L, LUA_REGISTRYINDEX, ctx->self_ref); /* func, self */
        lua_pushnil(L);                              /* func, self, nil */
        lua_pushstring(L, async_error_message(ctx, err, "conex\xC3\xA3o falhou")); /* func, self, nil, err */
        /* Now push dado and call */
        lua_rawgeti(L, LUA_REGISTRYINDEX, ctx->ref); /* func, self, nil, err, table */
        lua_getfield(L, -1, "dado");                 /* func, self, nil, err, table, dado */
        lua_remove(L, -2);                           /* func, self, nil, err, dado */
        if (lua_pcall(L, 4, 0, 0) != 0) {
            const char *errstr = lua_tostring(L, -1);
            /* rede conecteAssíncrono retorno erro: */
            g_printerr("rede conecteAss\xC3\xADncrono retorno erro: %s\n", errstr ? errstr : "(nulo)");
            lua_pop(L,1);
        }
        g_clear_error(&err);
        free_async_ctx(ctx);
        return;
    } else {
        /* success: push conn object and nil error */
        lua_rawgeti(L, LUA_REGISTRYINDEX, ctx->ref); /* table */
        lua_getfield(L, -1, "func");                 /* table, func */
        lua_remove(L, -2);                           /* func */
        lua_rawgeti(L, LUA_REGISTRYINDEX, ctx->self_ref); /* func, self */

        /* push new connection userdata */
        psock_conn_t *c = push_new_pconn(L);         /* func, self, conn_ud */
        c->conn = conn;
        c->istream = g_io_stream_get_input_stream(G_IO_STREAM(conn));
        c->ostream = g_io_stream_get_output_stream(G_IO_STREAM(conn));
        c->closed = FALSE;

        lua_pushnil(L);                              /* func, self, conn_ud, nil(err) */

        /* push dado and call */
        lua_rawgeti(L, LUA_REGISTRYINDEX, ctx->ref); /* func, self, conn_ud, nil, table */
        lua_getfield(L, -1, "dado");                 /* func, self, conn_ud, nil, table, dado */
        lua_remove(L, -2);                           /* func, self, conn_ud, nil, dado */

        if (lua_pcall(L, 4, 0, 0) != 0) {
            const char *errstr = lua_tostring(L, -1);
            /* rede conecteAssíncrono retorno erro: */
            g_printerr("rede conecteAss\xC3\xADncrono retorno erro: %s\n", errstr ? errstr : "(nulo)");
            lua_pop(L,1);
        }

        free_async_ctx(ctx);
        return;
    }
}

static int l_client_connect_async(lua_State *L) {
    psock_client_t *c = check_pclient(L,1);
    const char *host = p_getstring(L,2);
    int port = check_port(L, 3, FALSE);
    /* arg 4 precisa ser uma função */
    if (!lua_isfunction(L, 4)) return push_nil_err(L, "arg 4 precisa ser uma fun\xC3\xA7\xC3\xA3o");
    if (!c || c->closed) return push_nil_err(L,"cliente TCP inv\xC3\xA1lido");
    if (c->connect_pending) return push_nil_err(L, "conex\xC3\xA3o j\xC3\xA1 em andamento");

    async_ctx_t *ctx = create_async_ctx(L, 4, 5);
    ctx->client_owner = c;
    c->connect_pending = TRUE;
    c->connect_cancel = ctx->cancellable;
    arm_async_timeout(ctx, c->timeout_ms);

    GSocketConnectable *target = G_SOCKET_CONNECTABLE(g_network_address_new(host, port));
    g_socket_client_connect_async(c->client, target, ctx->cancellable, connect_finish_cb, ctx);
    g_object_unref(target);
    return 0;
}

/**
 * cliente:set_tls(use_tls_booleano)
 */
static int l_client_set_tls(lua_State *L) {
    psock_client_t *c = check_pclient(L, 1);
    /* cliente inválido */
    if (!c || c->closed) return push_nil_err(L, "cliente inv\xC3\xA1lido");
    gboolean use_tls = lua_toboolean(L, 2);

    g_socket_client_set_tls(c->client, use_tls);

    p_pushtrue(L);
    return 1;
}

/**
 * cliente:set_validacao_tls(validate_booleano)
 */
static int l_client_set_tls_validation(lua_State *L) {
    psock_client_t *c = check_pclient(L, 1);
    /* cliente inválido */
    if (!c || c->closed) return push_nil_err(L, "cliente inv\xC3\xA1lido");
    gboolean validate = lua_toboolean(L, 2);

    c->validate_tls = validate;
    p_pushtrue(L);
    return 1;
}

static guint check_timeout_ms(lua_State *L, int idx) {
    lua_Integer value = luaL_checkinteger(L, idx);
    luaL_argcheck(L, value >= 0 && (lua_Unsigned)value <= G_MAXUINT,
                  idx, "tempo limite fora do intervalo");
    return (guint)value;
}

static int l_client_set_timeout(lua_State *L) {
    psock_client_t *c = check_pclient(L, 1);
    if (!c || c->closed) return push_nil_err(L, "cliente inv\xC3\xA1lido");
    c->timeout_ms = check_timeout_ms(L, 2);
    lua_settop(L, 1);
    return 1;
}

static int l_client_cancel(lua_State *L) {
    psock_client_t *c = check_pclient(L, 1);
    gboolean pending = c && c->connect_pending && c->connect_cancel;
    if (pending) g_cancellable_cancel(c->connect_cancel);
    lua_pushboolean(L, pending);
    return 1;
}

static int l_server_set_timeout(lua_State *L) {
    psock_server_t *s = check_pserver(L, 1);
    if (!s || s->closed) return push_nil_err(L, "servidor inv\xC3\xA1lido");
    s->timeout_ms = check_timeout_ms(L, 2);
    lua_settop(L, 1);
    return 1;
}

static int l_server_cancel(lua_State *L) {
    psock_server_t *s = check_pserver(L, 1);
    gboolean pending = s && s->accept_pending && s->accept_cancel;
    if (pending) g_cancellable_cancel(s->accept_cancel);
    lua_pushboolean(L, pending);
    return 1;
}

static int l_conn_set_timeout(lua_State *L) {
    psock_conn_t *c = check_pconn(L, 1);
    if (!c || c->closed) return push_nil_err(L, "conex\xC3\xA3o inv\xC3\xA1lida");
    c->timeout_ms = check_timeout_ms(L, 2);
    lua_settop(L, 1);
    return 1;
}

static int l_conn_set_http_limits(lua_State *L) {
    psock_conn_t *c = check_pconn(L, 1);
    lua_Integer header = luaL_checkinteger(L, 2);
    lua_Integer body = luaL_checkinteger(L, 3);
    if (!c || c->closed) return push_nil_err(L, "conex\xC3\xA3o inv\xC3\xA1lida");
    if (header < 1024 || body < 0)
        return push_nil_err(L, "limites HTTP inv\xC3\xA1lidos");
    if ((lua_Unsigned)header > G_MAXSIZE || (lua_Unsigned)body > G_MAXSIZE)
        return push_nil_err(L, "limites HTTP grandes demais");
    c->max_header_bytes = (gsize)header;
    c->max_body_bytes = (gsize)body;
    lua_settop(L, 1);
    return 1;
}

static int l_conn_cancel(lua_State *L) {
    psock_conn_t *c = check_pconn(L, 1);
    gboolean pending = FALSE;
    if (c && c->read_pending && c->read_cancel) {
        g_cancellable_cancel(c->read_cancel);
        pending = TRUE;
    }
    if (c && c->write_pending && c->write_cancel) {
        g_cancellable_cancel(c->write_cancel);
        pending = TRUE;
    }
    lua_pushboolean(L, pending);
    return 1;
}

/* ---------------- SERVIDOR: bind, accept_async ---------------- */

static int l_server_bind(lua_State *L) {
    psock_server_t *s = check_pserver(L,1);
    const char *host = p_getstring(L,2);
    int port = check_port(L, 3, TRUE);
    if (!s || s->closed) return push_nil_err(L,"servidor TCP inv\xC3\xA1lido");

    GError *err = NULL;
    int ret = 0;

    GInetAddress *addr = g_inet_address_new_from_string(host);
    /* hospedeiro inválido */
    if (!addr) return push_nil_err(L,"endere\xC3\xA7o local inv\xC3\xA1lido; use um IPv4 ou IPv6 num\xC3\xA9rico");

    GSocketFamily family = g_inet_address_get_family(addr);
    GSocket *sock = g_socket_new(family, G_SOCKET_TYPE_STREAM, G_SOCKET_PROTOCOL_TCP, &err);
    if (!sock) {
        /* criação de tomada falhou */
        ret = push_nil_err(L, gio_error_message(err, "cria\xC3\xA7\xC3\xA3o do conector falhou"));
        if (err) g_clear_error(&err);
        g_object_unref(addr);
        return ret;
    }

    /* set SO_REUSEADDR: g_socket_set_option takes an int value, not pointer */
    {
        int reuse = 1;
        if (!g_socket_set_option(sock, SOL_SOCKET, SO_REUSEADDR, reuse, &err)) {
            /* non-fatal: try to continue but print an error */
            g_printerr("rede: falha ao definir SO_REUSEADDR: %s\n", gio_error_message(err, "erro desconhecido"));
            if (err) g_clear_error(&err);
        }
    }

    GSocketAddress *saddr = g_inet_socket_address_new(addr, port);
    g_object_unref(addr);

    gboolean ok = g_socket_bind(sock, saddr, TRUE, &err);
    g_object_unref(saddr);
    if (!ok) {
        ret = push_nil_err(L, gio_error_message(err, "amarre falhou"));
        if (err) g_clear_error(&err);
        g_object_unref(sock);
        return ret;
    }

    ok = g_socket_listen(sock, &err);
    if (!ok) {
        ret = push_nil_err(L, gio_error_message(err, "escute falhou"));
        if (err) g_clear_error(&err);
        g_object_unref(sock);
        return ret;
    }

    ok = g_socket_listener_add_socket(s->listener, sock, NULL, &err);
    g_object_unref(sock);

    if (!ok) {
        ret = push_nil_err(L, gio_error_message(err, "colocar conector para escutar falhou"));
        if (err) g_clear_error(&err);
        return ret;
    }

    p_pushtrue(L);
    return 1;
}

static void accept_finish_cb(GObject *source_object, GAsyncResult *res, gpointer user_data) {
    async_ctx_t *ctx = (async_ctx_t*) user_data;
    lua_State *L = ctx ? ctx->L : NULL;
    GError *err = NULL;

    GSocketConnection *conn = g_socket_listener_accept_finish(G_SOCKET_LISTENER(source_object), res, NULL, &err);

    clear_server_accept(ctx);

    if (!ctx || !L) {
        if (conn) g_object_unref(conn);
        if (err) g_clear_error(&err);
        free_async_ctx(ctx);
        return;
    }

    if (ctx->server_owner && ctx->server_owner->closed && conn) {
        g_io_stream_close(G_IO_STREAM(conn), NULL, NULL);
        g_object_unref(conn);
        conn = NULL;
        if (!err) g_set_error_literal(&err, G_IO_ERROR, G_IO_ERROR_CANCELLED,
                                      "servidor fechado");
    }

    if (err || !conn) {
        /* callback(self, nil, err_msg, dado) */
        lua_rawgeti(L, LUA_REGISTRYINDEX, ctx->ref); /* table */
        lua_getfield(L, -1, "func");                 /* table, func */
        lua_remove(L, -2);                           /* func */
        lua_rawgeti(L, LUA_REGISTRYINDEX, ctx->self_ref); /* func, self */
        lua_pushnil(L);                              /* func, self, nil */
        lua_pushstring(L, async_error_message(ctx, err, "aceite falhou")); /* func, self, nil, err */
        lua_rawgeti(L, LUA_REGISTRYINDEX, ctx->ref); /* func, self, nil, err, table */
        lua_getfield(L, -1, "dado");                 /* func, self, nil, err, table, dado */
        lua_remove(L, -2);                           /* func, self, nil, err, dado */
        if (lua_pcall(L, 4, 0, 0) != 0) {
            const char *errstr = lua_tostring(L, -1);
            /* rede aceiteAssíncrono retorno erro: */
            g_printerr("rede aceiteAss\xC3\xADncrono retorno erro: %s\n", errstr ? errstr : "(nulo)");
            lua_pop(L,1);
        }
        g_clear_error(&err);
        free_async_ctx(ctx);
        return;
    } else {
        /* callback(self, conn_obj, nil, dado) */
        lua_rawgeti(L, LUA_REGISTRYINDEX, ctx->ref); /* table */
        lua_getfield(L, -1, "func");                 /* table, func */
        lua_remove(L, -2);                           /* func */
        lua_rawgeti(L, LUA_REGISTRYINDEX, ctx->self_ref); /* func, self */

        psock_conn_t *c = push_new_pconn(L);         /* func, self, conn_ud */
        c->conn = conn;
        c->istream = g_io_stream_get_input_stream(G_IO_STREAM(conn));
        c->ostream = g_io_stream_get_output_stream(G_IO_STREAM(conn));
        c->closed = FALSE;

        lua_pushnil(L);                              /* func, self, conn_ud, nil */
        lua_rawgeti(L, LUA_REGISTRYINDEX, ctx->ref); /* func, self, conn_ud, nil, table */
        lua_getfield(L, -1, "dado");                 /* func, self, conn_ud, nil, table, dado */
        lua_remove(L, -2);                           /* func, self, conn_ud, nil, dado */

        if (lua_pcall(L, 4, 0, 0) != 0) {
            const char *errstr = lua_tostring(L, -1);
            /* rede aceiteAssíncrono retorno erro: */
            g_printerr("rede aceiteAss\xC3\xADncrono retorno erro: %s\n", errstr ? errstr : "(nulo)");
            lua_pop(L,1);
        }
        free_async_ctx(ctx);
        return;
    }
}

static int l_server_accept_async(lua_State *L) {
    psock_server_t *s = check_pserver(L,1);
    /* arg 2 precisa ser uma função */
    if (!lua_isfunction(L, 2)) return push_nil_err(L, "arg 2 precisa ser uma fun\xC3\xA7\xC3\xA3o");
    if (!s || s->closed) return push_nil_err(L,"servidor TCP n\xC3\xA3o est\xC3\xA1 escutando");
    if (s->accept_pending) return push_nil_err(L, "aceite j\xC3\xA1 em andamento");

    async_ctx_t *ctx = create_async_ctx(L, 2, 3);
    ctx->server_owner = s;
    s->accept_pending = TRUE;
    s->accept_cancel = ctx->cancellable;
    arm_async_timeout(ctx, s->timeout_ms);

    g_socket_listener_accept_async(s->listener, ctx->cancellable, accept_finish_cb, ctx);
    return 0;
}

/* ---------------- CONEXÃO: send_async, recv_async ---------------- */

static void send_finish_cb(GObject *source_object, GAsyncResult *res, gpointer user_data) {
    async_ctx_t *st = (async_ctx_t*) user_data;
    GOutputStream *ostream = G_OUTPUT_STREAM(source_object);
    GError *err = NULL;
    gsize n = 0;
    gboolean ok = g_output_stream_write_all_finish(ostream, res, &n, &err);
    lua_State *L = st ? st->L : NULL;

    clear_conn_write(st);

    if (!st || !L) {
        if (err) g_clear_error(&err);
        free_async_ctx(st);
        return;
    }

    if (ok) {
        /* func(self, n, nil, dado) */
        lua_rawgeti(L, LUA_REGISTRYINDEX, st->ref);
        lua_getfield(L, -1, "func");
        lua_remove(L, -2);
        lua_rawgeti(L, LUA_REGISTRYINDEX, st->self_ref);
        lua_pushinteger(L, (lua_Integer)n);
        lua_pushnil(L);
        lua_rawgeti(L, LUA_REGISTRYINDEX, st->ref);
        lua_getfield(L, -1, "dado");
        lua_remove(L, -2);
        if (lua_pcall(L, 4, 0, 0) != 0) {
            const char *errstr = lua_tostring(L, -1);
            g_printerr("rede enviarAss\xC3\xADncrono retornou erro: %s\n", errstr ? errstr : "(nulo)");
            lua_pop(L,1);
        }
    } else {
        /* func(self, nil, err_msg, dado) */
        lua_rawgeti(L, LUA_REGISTRYINDEX, st->ref);
        lua_getfield(L, -1, "func");
        lua_remove(L, -2);
        lua_rawgeti(L, LUA_REGISTRYINDEX, st->self_ref);
        lua_pushnil(L);
        /* falha no envio */
        lua_pushstring(L, async_error_message(st, err, "falha no envio"));
        if (err) g_clear_error(&err);
        lua_rawgeti(L, LUA_REGISTRYINDEX, st->ref);
        lua_getfield(L, -1, "dado");
        lua_remove(L, -2);
        if (lua_pcall(L, 4, 0, 0) != 0) {
            const char *errstr = lua_tostring(L, -1);
            g_printerr("rede enviarAss\xC3\xADncrono retornou erro: %s\n", errstr ? errstr : "(nulo)");
            lua_pop(L,1);
        }
    }

    free_async_ctx(st);
}

static int l_conn_send_async(lua_State *L) {
    psock_conn_t *c = check_pconn(L,1);
    size_t len = 0;
    const char *data = p_getlstring(L,2,&len);
    /* arg 3 precisa ser uma função */
    if (!lua_isfunction(L, 3)) return push_nil_err(L, "arg 3 precisa ser uma fun\xC3\xA7\xC3\xA3o");
    /* não conectado */
    if (!c || c->closed || !c->ostream) return push_nil_err(L,"n\xC3\xA3o conectado");
    if (c->write_pending) return push_nil_err(L, "envio j\xC3\xA1 em andamento");

    async_ctx_t *st = create_async_ctx(L, 3, 4);
    st->conn_owner = c;
    st->buffer = g_malloc(len > 0 ? len : 1);
    if (len > 0) memcpy(st->buffer, data, len);
    st->buflen = (gsize)len;
    c->write_pending = TRUE;
    c->write_cancel = st->cancellable;
    arm_async_timeout(st, c->timeout_ms);

    g_output_stream_write_all_async(c->ostream, st->buffer, st->buflen,
                                    G_PRIORITY_DEFAULT, st->cancellable,
                                    send_finish_cb, st);
    return 0;
}

typedef enum {
    HTTP_FRAME_INCOMPLETO = 0,
    HTTP_FRAME_COMPLETO,
    HTTP_FRAME_ERRO
} http_frame_result_t;

static const guint8 *find_http_header_end(const guint8 *buf, gsize len,
                                          gsize *header_len) {
    for (gsize i = 0; i + 1 < len; i++) {
        if (i + 3 < len && buf[i] == '\r' && buf[i + 1] == '\n' &&
            buf[i + 2] == '\r' && buf[i + 3] == '\n') {
            *header_len = i + 4;
            return buf + i;
        }
        if (buf[i] == '\n' && buf[i + 1] == '\n') {
            *header_len = i + 2;
            return buf + i;
        }
    }
    return NULL;
}

static gboolean ascii_header_name_equal(const char *start, const char *end,
                                        const char *expected) {
    gsize len = (gsize)(end - start);
    return strlen(expected) == len && g_ascii_strncasecmp(start, expected, len) == 0;
}

static http_frame_result_t inspect_http_frame(async_ctx_t *st,
                                              gsize *complete_len,
                                              const char **message) {
    psock_conn_t *c = st->conn_owner;
    const guint8 *buf = st->accum->data;
    gsize len = st->accum->len;
    gsize header_len = 0;

    if (!find_http_header_end(buf, len, &header_len)) {
        if ((c && len > c->max_header_bytes) || len > st->max_total) {
            *message = "cabe\xC3\xA7" "alho HTTP excede o limite";
            return HTTP_FRAME_ERRO;
        }
        return HTTP_FRAME_INCOMPLETO;
    }

    if ((c && header_len > c->max_header_bytes) || header_len > st->max_total) {
        *message = "cabe\xC3\xA7" "alho HTTP excede o limite";
        return HTTP_FRAME_ERRO;
    }

    gboolean saw_content_length = FALSE;
    gboolean saw_transfer_encoding = FALSE;
    guint64 content_length = 0;
    const char *p = (const char*)buf;
    const char *headers_end = (const char*)buf + header_len;
    const char *line = find_crlf(p, headers_end);
    if (!line) return HTTP_FRAME_INCOMPLETO;
    p = (*line == '\r' && line + 1 < headers_end && line[1] == '\n') ? line + 2 : line + 1;

    while (p < headers_end) {
        const char *line_end = find_crlf(p, headers_end);
        if (!line_end) break;
        if (line_end == p) break;
        const char *colon = memchr(p, ':', (size_t)(line_end - p));
        if (colon) {
            const char *name_start = p;
            const char *name_end = colon;
            const char *value_start = colon + 1;
            const char *value_end = line_end;
            trim_ascii(&name_start, &name_end);
            trim_ascii(&value_start, &value_end);

            if (ascii_header_name_equal(name_start, name_end, "Content-Length")) {
                if (saw_content_length) {
                    *message = "Content-Length repetido";
                    return HTTP_FRAME_ERRO;
                }
                saw_content_length = TRUE;
                char *value = g_strndup(value_start, (gsize)(value_end - value_start));
                char *tail = NULL;
                errno = 0;
                guint64 parsed = g_ascii_strtoull(value, &tail, 10);
                gboolean digits_only = value[0] != '\0';
                for (const char *digit = value; *digit; digit++)
                    if (!g_ascii_isdigit(*digit)) { digits_only = FALSE; break; }
                gboolean valid = digits_only && errno == 0 && tail && *tail == '\0';
                g_free(value);
                if (!valid) {
                    *message = "Content-Length inv\xC3\xA1lido";
                    return HTTP_FRAME_ERRO;
                }
                content_length = parsed;
            } else if (ascii_header_name_equal(name_start, name_end, "Transfer-Encoding")) {
                saw_transfer_encoding = TRUE;
            }
        }
        p = (*line_end == '\r' && line_end + 1 < headers_end && line_end[1] == '\n')
            ? line_end + 2 : line_end + 1;
    }

    if (saw_transfer_encoding) {
        *message = "Transfer-Encoding ainda n\xC3\xA3o \xC3\xA9 aceito";
        return HTTP_FRAME_ERRO;
    }
    if (c && content_length > c->max_body_bytes) {
        *message = "corpo HTTP excede o limite";
        return HTTP_FRAME_ERRO;
    }
    if (content_length > G_MAXSIZE - header_len ||
        header_len + (gsize)content_length > st->max_total) {
        *message = "requisi\xC3\xA7\xC3\xA3o HTTP excede o limite total";
        return HTTP_FRAME_ERRO;
    }

    *complete_len = header_len + (gsize)content_length;
    return len >= *complete_len ? HTTP_FRAME_COMPLETO : HTTP_FRAME_INCOMPLETO;
}

static void add_peer_info(lua_State *L, int req_index, psock_conn_t *c) {
    if (!c || !c->conn || !lua_istable(L, req_index)) return;
    req_index = lua_absindex(L, req_index);
    GError *err = NULL;
    GSocketAddress *addr = g_socket_connection_get_remote_address(c->conn, &err);
    if (addr && G_IS_INET_SOCKET_ADDRESS(addr)) {
        GInetSocketAddress *inet = G_INET_SOCKET_ADDRESS(addr);
        gchar *ip = g_inet_address_to_string(g_inet_socket_address_get_address(inet));
        lua_pushstring(L, ip);
        lua_setfield(L, req_index, "ip");
        lua_pushinteger(L, g_inet_socket_address_get_port(inet));
        lua_setfield(L, req_index, "portaRemota");
        g_free(ip);
    }
    if (addr) g_object_unref(addr);
    if (err) g_clear_error(&err);
}

static void invoke_stream_callback(async_ctx_t *st, const guint8 *data,
                                   gsize len, const char *message) {
    lua_State *L = st->L;
    clear_conn_read(st);

    lua_rawgeti(L, LUA_REGISTRYINDEX, st->ref);
    lua_getfield(L, -1, "func");
    lua_remove(L, -2);
    lua_rawgeti(L, LUA_REGISTRYINDEX, st->self_ref);

    if (message) {
        lua_pushnil(L);
        lua_pushstring(L, message);
    } else if (st->parse_http) {
        lua_pushcfunction(L, l_rede_analiseHTTP);
        lua_pushlstring(L, (const char*)data, len);
        if (lua_pcall(L, 1, 2, 0) != LUA_OK) {
            const char *e = lua_tostring(L, -1);
            lua_pop(L, 1);
            lua_pushnil(L);
            lua_pushstring(L, e ? e : "an\xC3\xA1lise HTTP falhou");
        }
        if (lua_istable(L, -2)) add_peer_info(L, -2, st->conn_owner);
    } else {
        lua_pushlstring(L, (const char*)data, len);
        lua_pushnil(L);
    }

    lua_rawgeti(L, LUA_REGISTRYINDEX, st->ref);
    lua_getfield(L, -1, "dado");
    lua_remove(L, -2);
    if (lua_pcall(L, 4, 0, 0) != LUA_OK) {
        const char *errstr = lua_tostring(L, -1);
        g_printerr("rede receberAss\xC3\xADncrono retorno erro: %s\n",
                   errstr ? errstr : "(nulo)");
        lua_pop(L, 1);
    }
    free_async_ctx(st);
}

static void recv_finish_cb(GObject *source_object, GAsyncResult *res, gpointer user_data) {
    async_ctx_t *st = (async_ctx_t*)user_data;
    GInputStream *istream = G_INPUT_STREAM(source_object);
    GError *err = NULL;
    gssize n = g_input_stream_read_finish(istream, res, &err);

    if (!st || !st->L) {
        if (err) g_clear_error(&err);
        free_async_ctx(st);
        return;
    }

    if (n <= 0) {
        const char *message = async_error_message(
            st, err, st->parse_http ? "conex\xC3\xA3o fechada antes da requisi\xC3\xA7\xC3\xA3o completa" : "conex\xC3\xA3o fechada");
        invoke_stream_callback(st, NULL, 0, message);
        if (err) g_clear_error(&err);
        return;
    }

    if (!st->parse_http) {
        invoke_stream_callback(st, (const guint8*)st->buffer, (gsize)n, NULL);
        return;
    }

    g_byte_array_append(st->accum, (const guint8*)st->buffer, (guint)n);
    gsize complete_len = 0;
    const char *message = NULL;
    http_frame_result_t frame = inspect_http_frame(st, &complete_len, &message);
    if (frame == HTTP_FRAME_ERRO) {
        invoke_stream_callback(st, NULL, 0, message);
        return;
    }
    if (frame == HTTP_FRAME_COMPLETO) {
        invoke_stream_callback(st, st->accum->data, complete_len, NULL);
        return;
    }

    g_input_stream_read_async(istream, st->buffer, st->buflen,
                              G_PRIORITY_DEFAULT, st->cancellable,
                              recv_finish_cb, st);
}

static int start_conn_receive(lua_State *L, gboolean parse_http) {
    psock_conn_t *c = check_pconn(L, 1);
    lua_Integer max_arg = luaL_checkinteger(L, 2);
    if (!lua_isfunction(L, 3))
        return push_nil_err(L, "arg 3 precisa ser uma fun\xC3\xA7\xC3\xA3o");
    if (!c || c->closed || !c->istream)
        return push_nil_err(L, "n\xC3\xA3o conectado");
    if (c->read_pending)
        return push_nil_err(L, "leitura j\xC3\xA1 em andamento");
    if (max_arg <= 0) max_arg = 4096;
    if ((lua_Unsigned)max_arg > G_MAXSIZE ||
        (!parse_http && (lua_Unsigned)max_arg > REDE_LEITURA_CRUA_MAX))
        return push_nil_err(L, "limite de leitura grande demais");
    gsize max = (gsize)max_arg;

    async_ctx_t *st = create_async_ctx(L, 3, 4);
    st->conn_owner = c;
    st->parse_http = parse_http;
    st->max_total = max;
    st->buflen = parse_http ? MIN((gsize)REDE_HTTP_CHUNK, max) : max;
    st->buffer = g_malloc(st->buflen > 0 ? st->buflen : 1);
    if (parse_http) st->accum = g_byte_array_sized_new(st->buflen);

    c->read_pending = TRUE;
    c->read_cancel = st->cancellable;
    arm_async_timeout(st, c->timeout_ms);
    g_input_stream_read_async(c->istream, st->buffer, st->buflen,
                              G_PRIORITY_DEFAULT, st->cancellable,
                              recv_finish_cb, st);
    return 0;
}

static int l_conn_recv_async(lua_State *L) {
    return start_conn_receive(L, TRUE);
}

static int l_conn_recv_data_async(lua_State *L) {
    return start_conn_receive(L, FALSE);
}

/* ---------------- UDP ---------------- */

static int l_udp_gc(lua_State *L) {
    /* rede{udp} */
    psock_udp_t *u = (psock_udp_t*) luaL_checkudata(L, 1, "rede{udp}");
    if (u && !u->closed) {
        if (u->recv_source_id > 0) {
            g_source_remove(u->recv_source_id);
            u->recv_source_id = 0;
        }
        /* A referência de recepção pertence ao estado associado ao GSource;
         * o destruidor do source a libera exatamente uma vez. */
        u->recv_ref = LUA_NOREF;
        if (u->send_cancel) g_cancellable_cancel(u->send_cancel);
        if (u->socket) g_object_unref(u->socket);
        u->socket = NULL;
        u->closed = TRUE;
    }
    return 0;
}

static int l_udp_close(lua_State *L) {
    l_udp_gc(L);
    p_pushtrue(L);
    return 1;
}

static int l_rede_udp(lua_State *L) {
    psock_udp_t *u = (psock_udp_t*) lua_newuserdata(L, sizeof(psock_udp_t));
    memset(u, 0, sizeof(*u));
    u->recv_ref = LUA_NOREF;
    const char *family_name = luaL_optstring(L, 1, "IPv4");
    GSocketFamily family;
    if (g_ascii_strcasecmp(family_name, "IPv4") == 0)
        family = G_SOCKET_FAMILY_IPV4;
    else if (g_ascii_strcasecmp(family_name, "IPv6") == 0)
        family = G_SOCKET_FAMILY_IPV6;
    else
        return push_nil_err(L, "fam\xC3\xADlia deve ser IPv4 ou IPv6");

    GError *err = NULL;
    u->socket = g_socket_new(family, G_SOCKET_TYPE_DATAGRAM, G_SOCKET_PROTOCOL_UDP, &err);
    if (!u->socket) {
        /* criação de udp falhou */
        int ret = push_nil_err(L, gio_error_message(err, "cria\xC3\xA7\xC3\xA3o de UDP falhou"));
        if (err) g_clear_error(&err);
        return ret;
    }
    g_socket_set_blocking(u->socket, FALSE);
    u->closed = FALSE;
    u->timeout_ms = 0;
    /* rede{udp} */
    luaL_getmetatable(L, "rede{udp}");
    lua_setmetatable(L, -2);
    return 1;
}

static int l_udp_bind(lua_State *L) {
    psock_udp_t *u = check_pudp(L, 1);
    const char *host = p_getstring(L, 2);
    int port = check_port(L, 3, TRUE);
    if (!u || u->closed) return push_nil_err(L, "conector UDP inv\xC3\xA1lido");

    GError *err = NULL;
    GInetAddress *addr = g_inet_address_new_from_string(host);
    /* hospedeiro inválido */
    if (!addr) return push_nil_err(L, "hospedeiro inv\xC3\xA1lido");
    GSocketAddress *saddr = g_inet_socket_address_new(addr, port);

    {
        int reuse = 1;
        if (!g_socket_set_option(u->socket, SOL_SOCKET, SO_REUSEADDR, reuse, &err)) {
            g_printerr("rede: UDP falhou ao definir SO_REUSEADDR: %s\n", gio_error_message(err, "erro desconhecido"));
            if (err) g_clear_error(&err);
        }
    }

    gboolean ok = g_socket_bind(u->socket, saddr, TRUE, &err);
    g_object_unref(saddr);
    g_object_unref(addr);

    if (!ok) {
        /* amarre udp falhou */
        int ret = push_nil_err(L, gio_error_message(err, "amarre UDP falhou"));
        if (err) g_clear_error(&err);
        return ret;
    }
    p_pushtrue(L);
    return 1;
}

static int l_udp_sendto(lua_State *L) {
    psock_udp_t *u = check_pudp(L, 1);
    const char *host = p_getstring(L, 2);
    int port = check_port(L, 3, FALSE);
    size_t len = 0;
    const char *data = p_getlstring(L, 4, &len);
    if (!u || u->closed) return push_nil_err(L, "conector UDP inv\xC3\xA1lido");

    GInetAddress *addr = g_inet_address_new_from_string(host);
    /* hospedeiro inválido */
    if (!addr) return push_nil_err(L, "hospedeiro inv\xC3\xA1lido");
    GSocketAddress *saddr = g_inet_socket_address_new(addr, port);

    GError *err = NULL;
    gssize n = g_socket_send_to(u->socket, saddr, data, (gsize)len, NULL, &err);
    g_object_unref(saddr);
    g_object_unref(addr);

    if (n < 0) {
        /* enviarPara falhou */
        int ret = push_nil_err(L, gio_error_message(err, "enviePara falhou"));
        if (err) g_clear_error(&err);
        return ret;
    }
    p_pushinteger(L, (lua_Integer)n);
    return 1;
}

static void udp_send_state_destroy(gpointer user_data) {
    udp_send_state_t *st = (udp_send_state_t*)user_data;
    if (!st) return;
    if (st->owner) {
        if (st->owner->send_source_id == st->source_id) {
            st->owner->send_pending = FALSE;
            st->owner->send_source_id = 0;
            st->owner->send_timeout_id = 0;
        }
        if (st->ctx && st->owner->send_cancel == st->ctx->cancellable)
            st->owner->send_cancel = NULL;
    }
    if (st->dest) g_object_unref(st->dest);
    free_async_ctx(st->ctx);
    g_free(st);
}

static void invoke_udp_send_callback(udp_send_state_t *st, gssize sent,
                                     const char *message) {
    async_ctx_t *ctx = st->ctx;
    lua_State *L = ctx->L;
    if (st->owner) {
        st->owner->send_pending = FALSE;
        if (st->owner->send_cancel == ctx->cancellable)
            st->owner->send_cancel = NULL;
    }

    lua_rawgeti(L, LUA_REGISTRYINDEX, ctx->ref);
    lua_getfield(L, -1, "func");
    lua_remove(L, -2);
    lua_rawgeti(L, LUA_REGISTRYINDEX, ctx->self_ref);
    if (message) {
        lua_pushnil(L);
        lua_pushstring(L, message);
    } else {
        lua_pushinteger(L, (lua_Integer)sent);
        lua_pushnil(L);
    }
    lua_rawgeti(L, LUA_REGISTRYINDEX, ctx->ref);
    lua_getfield(L, -1, "dado");
    lua_remove(L, -2);
    if (lua_pcall(L, 4, 0, 0) != LUA_OK) {
        const char *e = lua_tostring(L, -1);
        g_printerr("rede envieParaAss\xC3\xADncrono retorno erro: %s\n",
                   e ? e : "(nulo)");
        lua_pop(L, 1);
    }
}

static gboolean udp_send_source_func(GSocket *socket, GIOCondition condition,
                                     gpointer user_data) {
    udp_send_state_t *st = (udp_send_state_t*)user_data;
    async_ctx_t *ctx = st->ctx;
    if (g_cancellable_is_cancelled(ctx->cancellable)) {
        invoke_udp_send_callback(st, -1,
            ctx->timed_out ? "tempo limite excedido" : "opera\xC3\xA7\xC3\xA3o cancelada");
        return G_SOURCE_REMOVE;
    }

    if (condition & (G_IO_ERR | G_IO_HUP | G_IO_NVAL)) {
        invoke_udp_send_callback(st, -1, "conector UDP indispon\xC3\xADvel");
        return G_SOURCE_REMOVE;
    }

    GError *err = NULL;
    gssize sent = g_socket_send_to(socket, st->dest, ctx->buffer, ctx->buflen,
                                   ctx->cancellable, &err);
    if (sent < 0 && err && g_error_matches(err, G_IO_ERROR, G_IO_ERROR_WOULD_BLOCK)) {
        g_clear_error(&err);
        return G_SOURCE_CONTINUE;
    }
    if (sent < 0) {
        const char *message = async_error_message(ctx, err, "envio UDP falhou");
        char *copy = g_strdup(message);
        if (err) g_clear_error(&err);
        invoke_udp_send_callback(st, -1, copy);
        g_free(copy);
        return G_SOURCE_REMOVE;
    }
    if ((gsize)sent != ctx->buflen) {
        invoke_udp_send_callback(st, -1, "datagrama enviado parcialmente");
        return G_SOURCE_REMOVE;
    }
    invoke_udp_send_callback(st, sent, NULL);
    return G_SOURCE_REMOVE;
}

static int l_udp_sendto_async(lua_State *L) {
    psock_udp_t *u = check_pudp(L, 1);
    const char *host = p_getstring(L, 2);
    int port = check_port(L, 3, FALSE);
    size_t len = 0;
    const char *data = p_getlstring(L, 4, &len);
    if (!lua_isfunction(L, 5))
        return push_nil_err(L, "arg 5 precisa ser uma fun\xC3\xA7\xC3\xA3o");
    if (!u || u->closed) return push_nil_err(L, "conector UDP inv\xC3\xA1lido");
    if (u->send_pending) return push_nil_err(L, "envio UDP j\xC3\xA1 em andamento");

    GInetAddress *addr = g_inet_address_new_from_string(host);
    if (!addr) return push_nil_err(L, "endere\xC3\xA7o IP inv\xC3\xA1lido");

    udp_send_state_t *st = g_new0(udp_send_state_t, 1);
    st->owner = u;
    st->ctx = create_async_ctx(L, 5, 6);
    st->ctx->buffer = g_malloc(len > 0 ? len : 1);
    if (len > 0) memcpy(st->ctx->buffer, data, len);
    st->ctx->buflen = (gsize)len;
    st->dest = g_inet_socket_address_new(addr, port);
    g_object_unref(addr);

    GSource *source = g_socket_create_source(u->socket,
        (GIOCondition)(G_IO_OUT | G_IO_ERR | G_IO_HUP), st->ctx->cancellable);
    g_source_set_callback(source, G_SOURCE_FUNC(udp_send_source_func), st,
                          udp_send_state_destroy);
    st->source_id = g_source_attach(source, NULL);
    g_source_unref(source);

    u->send_pending = TRUE;
    u->send_source_id = st->source_id;
    u->send_cancel = st->ctx->cancellable;
    arm_async_timeout(st->ctx, u->timeout_ms);
    u->send_timeout_id = st->ctx->timeout_id;
    return 0;
}

/* O callback de GSocketSource recebe (socket, condição, dado). */
static gboolean udp_source_func(GSocket *socket, GIOCondition condition,
                                gpointer user_data) {
    udp_recv_state_t *st = (udp_recv_state_t*)user_data;
    if (!st || !socket || !st->L || st->ref == LUA_NOREF)
        return G_SOURCE_REMOVE;

    lua_State *L = st->L;
    GError *err = NULL;
    GSocketAddress *from = NULL;
    gssize n = -1;

    if (!(condition & (G_IO_ERR | G_IO_HUP | G_IO_NVAL)))
        n = g_socket_receive_from(socket, &from, st->buffer, st->maxlen, NULL, &err);

    if (n < 0 && err && g_error_matches(err, G_IO_ERROR, G_IO_ERROR_WOULD_BLOCK)) {
        g_clear_error(&err);
        return G_SOURCE_CONTINUE;
    }

    lua_rawgeti(L, LUA_REGISTRYINDEX, st->ref);
    lua_getfield(L, -1, "func");
    lua_remove(L, -2);

    if (n >= 0) {
        lua_pushlstring(L, (const char*)st->buffer, (size_t)n);
        lua_pushnil(L);
        if (from && G_IS_INET_SOCKET_ADDRESS(from)) {
            GInetSocketAddress *ia = G_INET_SOCKET_ADDRESS(from);
            gchar *ip = g_inet_address_to_string(
                g_inet_socket_address_get_address(ia));
            lua_pushstring(L, ip);
            lua_pushinteger(L, g_inet_socket_address_get_port(ia));
            g_free(ip);
        } else {
            lua_pushnil(L);
            lua_pushnil(L);
        }
    } else {
        lua_pushnil(L);
        lua_pushstring(L, gio_error_message(err, "erro ao receber UDP"));
        lua_pushnil(L);
        lua_pushnil(L);
    }

    lua_rawgeti(L, LUA_REGISTRYINDEX, st->ref);
    lua_getfield(L, -1, "dado");
    lua_remove(L, -2);
    if (lua_pcall(L, 5, 0, 0) != LUA_OK) {
        const char *e = lua_tostring(L, -1);
        g_printerr("rede recep\xC3\xA7\xC3\xA3o UDP retorno erro: %s\n",
                   e ? e : "(nulo)");
        lua_pop(L, 1);
    }

    if (from) g_object_unref(from);
    if (err) g_clear_error(&err);
    return n >= 0 ? G_SOURCE_CONTINUE : G_SOURCE_REMOVE;
}

static int l_udp_recv_start(lua_State *L) {
    psock_udp_t *u = check_pudp(L, 1);
    lua_Integer max_arg = luaL_checkinteger(L, 2);
    /* arg 3 precisa ser uma função */
    if (!lua_isfunction(L, 3)) return push_nil_err(L, "arg 3 precisa ser uma fun\xC3\xA7\xC3\xA3o");
    /* tomada udp inválida */
    if (!u || u->closed) return push_nil_err(L, "conector UDP inv\xC3\xA1lido");
    /* já está recebendo */
    if (u->recv_source_id > 0) return push_nil_err(L, "j\xC3\xA1 est\xC3\xA1 recebendo");
    if (max_arg <= 0) max_arg = 4096;
    if ((lua_Unsigned)max_arg > G_MAXSIZE ||
        (lua_Unsigned)max_arg > REDE_LEITURA_CRUA_MAX)
        return push_nil_err(L, "limite de datagrama grande demais");
    gsize max = (gsize)max_arg;

    udp_recv_state_t *st = g_new0(udp_recv_state_t, 1);
    st->L = L;
    st->socket = g_object_ref(u->socket);
    st->maxlen = max;
    st->buffer = g_malloc(st->maxlen);
    st->ref = store_callback(L, 3, 4);
    st->owner = u;

    u->recv_ref = st->ref;

    GSource *source = g_socket_create_source(u->socket, G_IO_IN, NULL);
    g_source_set_callback(source, G_SOURCE_FUNC(udp_source_func), st,
                          udp_state_destroy_notify);

    u->recv_source_id = g_source_attach(source, NULL);
    g_source_unref(source);

    p_pushtrue(L);
    return 1;
}

static int l_udp_recv_stop(lua_State *L) {
    psock_udp_t *u = check_pudp(L, 1);
    if (u && u->recv_source_id > 0) {
        g_source_remove(u->recv_source_id);
        u->recv_source_id = 0;
        u->recv_ref = LUA_NOREF;
    }
    p_pushtrue(L);
    return 1;
}

static int l_udp_set_timeout(lua_State *L) {
    psock_udp_t *u = check_pudp(L, 1);
    if (!u || u->closed) return push_nil_err(L, "conector UDP inv\xC3\xA1lido");
    u->timeout_ms = check_timeout_ms(L, 2);
    lua_settop(L, 1);
    return 1;
}

static int l_udp_cancel(lua_State *L) {
    psock_udp_t *u = check_pudp(L, 1);
    gboolean pending = FALSE;
    if (u && u->recv_source_id > 0) {
        g_source_remove(u->recv_source_id);
        u->recv_source_id = 0;
        u->recv_ref = LUA_NOREF;
        pending = TRUE;
    }
    if (u && u->send_pending && u->send_cancel) {
        g_cancellable_cancel(u->send_cancel);
        pending = TRUE;
    }
    lua_pushboolean(L, pending);
    return 1;
}

static int l_rede_loop(lua_State *L) {
    if (rede_main_loop && g_main_loop_is_running(rede_main_loop))
        return push_nil_err(L, "o la\xC3\xA7o de eventos j\xC3\xA1 est\xC3\xA1 rodando");
    if (rede_main_loop) g_main_loop_unref(rede_main_loop);
    rede_main_loop = g_main_loop_new(NULL, FALSE);
    g_main_loop_run(rede_main_loop);
    g_main_loop_unref(rede_main_loop);
    rede_main_loop = NULL;
    return 0;
}

static int l_rede_stop_loop(lua_State *L) {
    gboolean running = rede_main_loop && g_main_loop_is_running(rede_main_loop);
    if (running) g_main_loop_quit(rede_main_loop);
    lua_pushboolean(L, running);
    return 1;
}
static int l_rede_nova_res(lua_State *L) {
    psock_conn_t *conn = check_pconn(L, 1);
    /* conexão inválida */
    if (!conn || conn->closed)
        return push_nil_err(L, "conex\xC3\xA3o inv\xC3\xA1lida");

    psock_res_t *r = (psock_res_t*) lua_newuserdata(L, sizeof(psock_res_t));
    r->conn = conn;
    r->status = 200;
    r->headers = g_hash_table_new_full(header_hash_ci, header_equal_ci, g_free, g_free);

    /* rede{res} */
    luaL_getmetatable(L, "rede{res}");
    lua_setmetatable(L, -2);

    return 1;
}

/* ---------- rede.http_resposta(status, corpo, [content_type]) ---------- */
/* Gera uma string HTTP completa para enviar via send_async */

static int l_rede_http_resposta(lua_State *L) {
    lua_Integer status_arg = luaL_checkinteger(L, 1);
    int status = (int)status_arg;
    if (status_arg < 100 || status_arg > 599)
        return push_nil_err(L, "c\xC3\xB3" "digo HTTP fora do intervalo 100..599");

    size_t body_len = 0;
    const char *body = p_getlstring(L, 2, &body_len);
    if (!body) {
        body = "";
        body_len = 0;
    }

    const char *content_type = NULL;
    if (lua_gettop(L) >= 3 && !lua_isnoneornil(L, 3)) {
        size_t type_len = 0;
        content_type = luaL_checklstring(L, 3, &type_len);
        if (!header_value_valid(content_type, type_len))
            return push_nil_err(L, "tipo de conte\xC3\xBA" "do inv\xC3\xA1lido");
    } else {
        content_type = "text/html; charset=utf-8";
    }

    const char *reason = http_reason_phrase(status);

    /* Monta resposta em GString */
    GString *g = g_string_sized_new(body_len + 256);

    g_string_append_printf(g, "HTTP/1.1 %d %s\r\n", status, reason);
    g_string_append_printf(g, "Content-Type: %s\r\n", content_type);
    g_string_append_printf(g, "Content-Length: %zu\r\n", (size_t)body_len);
    g_string_append(g, "Connection: close\r\n");
    g_string_append(g, "\r\n");

    if (body_len > 0) {
        g_string_append_len(g, body, (gssize)body_len);
    }

    lua_pushlstring(L, g->str, (size_t)g->len);
    g_string_free(g, TRUE);

    return 1;
}

/* ---------- rede.analiseHTTP(dados) ---------- */

static int http_parse_fail(lua_State *L, const char *message) {
    lua_settop(L, 1); /* conserva somente o argumento original */
    lua_pushnil(L);
    lua_pushstring(L, message);
    return 2;
}

static int l_rede_analiseHTTP(lua_State *L) {
    size_t len = 0;
    const char *buf = p_getlstring(L, 1, &len);
    if (!buf || len == 0) {
        p_pushnil(L);
        p_pushstring(L, "dados HTTP vazios");
        return 2;
    }
    if (len > REDE_HTTP_HEADER_PADRAO + REDE_HTTP_CORPO_PADRAO) {
        p_pushnil(L);
        p_pushstring(L, "requisi\xC3\xA7\xC3\xA3o HTTP excede o limite total");
        return 2;
    }

    psock_conn_t limits;
    memset(&limits, 0, sizeof(limits));
    limits.max_header_bytes = REDE_HTTP_HEADER_PADRAO;
    limits.max_body_bytes = REDE_HTTP_CORPO_PADRAO;
    async_ctx_t frame_ctx;
    memset(&frame_ctx, 0, sizeof(frame_ctx));
    frame_ctx.accum = g_byte_array_sized_new(len);
    g_byte_array_append(frame_ctx.accum, (const guint8*)buf, (guint)len);
    frame_ctx.conn_owner = &limits;
    frame_ctx.max_total = REDE_HTTP_HEADER_PADRAO + REDE_HTTP_CORPO_PADRAO;
    gsize complete_len = 0;
    const char *frame_message = NULL;
    http_frame_result_t frame = inspect_http_frame(&frame_ctx, &complete_len,
                                                   &frame_message);
    g_byte_array_unref(frame_ctx.accum);
    if (frame != HTTP_FRAME_COMPLETO) {
        p_pushnil(L);
        p_pushstring(L, frame == HTTP_FRAME_ERRO ? frame_message :
                     "requisi\xC3\xA7\xC3\xA3o HTTP incompleta");
        return 2;
    }
    len = complete_len;

    const char *p = buf;
    const char *end = buf + len;

    /* 1) Linha de requisição: "METODO CAMINHO versão" */
    const char *line_end = find_crlf(p, end);
    if (!line_end) {
        p_pushnil(L);
        /* linha de requisição incompleta */
        p_pushstring(L, "linha de requisi\xC3\xA7\xC3\xA3o incompleta");
        return 2;
    }

    const char *req_line_start = p;
    const char *req_line_end = line_end;

    /* avança após CRLF */
    if (*line_end == '\r' && line_end + 1 < end && line_end[1] == '\n')
        p = line_end + 2;
    else
        p = line_end + 1;

    /* parse método, caminho, versão */
    const char *m_start = req_line_start;
    const char *m_end = m_start;
    while (m_end < req_line_end && *m_end != ' ') m_end++;

    if (m_end == req_line_end) {
        p_pushnil(L);
        /* linha de requisição sem caminho */
        p_pushstring(L, "linha de requisi\xC3\xA7\xC3\xA3o sem caminho");
        return 2;
    }

    const char *path_start = m_end + 1;
    const char *path_end = path_start;
    while (path_end < req_line_end && *path_end != ' ') path_end++;

    const char *vers_start = NULL;
    const char *vers_end = NULL;

    if (path_end < req_line_end) {
        vers_start = path_end + 1;
        vers_end = req_line_end;
    }

    trim_ascii(&m_start, &m_end);
    trim_ascii(&path_start, &path_end);
    if (vers_start && vers_end) trim_ascii(&vers_start, &vers_end);

    if (m_end <= m_start || path_end <= path_start) {
        p_pushnil(L);
        /* método ou caminho vazio */
        p_pushstring(L, "m\xC3\xA9todo ou caminho vazio");
        return 2;
    }
    if (!header_name_valid(m_start, (size_t)(m_end - m_start)))
        return http_parse_fail(L, "m\xC3\xA9todo HTTP inv\xC3\xA1lido");
    for (const char *scan = path_start; scan < path_end; scan++) {
        unsigned char c = (unsigned char)*scan;
        if (c <= 0x20 || c == 0x7f)
            return http_parse_fail(L, "caminho HTTP cont\xC3\xA9m caractere inv\xC3\xA1lido");
    }

    gboolean is_http11 = FALSE;
    if (vers_start && vers_end && vers_end > vers_start) {
        size_t vers_len = (size_t)(vers_end - vers_start);
        gboolean is_http10 = vers_len == 8 && memcmp(vers_start, "HTTP/1.0", 8) == 0;
        is_http11 = vers_len == 8 && memcmp(vers_start, "HTTP/1.1", 8) == 0;
        if (!is_http10 && !is_http11)
            return http_parse_fail(L, "vers\xC3\xA3o HTTP n\xC3\xA3o aceita");
    }

    /* cria tabela req */
    lua_newtable(L); /* req */

    lua_pushlstring(L, m_start, (size_t)(m_end - m_start));
    lua_setfield(L, -2, "método");

    /* separa caminho e querystring */
    const char *qmark = memchr(path_start, '?', (size_t)(path_end - path_start));
    if (qmark) {
        /* caminho antes de '?' */
        lua_pushlstring(L, path_start, (size_t)(qmark - path_start));
        lua_setfield(L, -2, "caminho");

        /* tabela de consulta */
        lua_newtable(L); /* req, consulta */
        const char *query_message = NULL;
        if (!parse_query_string(L, qmark + 1,
                                (size_t)(path_end - (qmark + 1)),
                                &query_message)) {
            lua_pop(L, 2); /* consulta e req */
            p_pushnil(L);
            p_pushstring(L, query_message ? query_message : "consulta inv\xC3\xA1lida");
            return 2;
        }
        lua_setfield(L, -2, "consulta");
    } else {
        lua_pushlstring(L, path_start, (size_t)(path_end - path_start));
        lua_setfield(L, -2, "caminho");

        lua_newtable(L);
        lua_setfield(L, -2, "consulta");
    }

    if (vers_start && vers_end && vers_end > vers_start) {
        lua_pushlstring(L, vers_start, (size_t)(vers_end - vers_start));
        /* versão */
        lua_setfield(L, -2, "vers\xC3\xA3o");
    } else {
        lua_pushstring(L, "HTTP/1.0");
        /* versão */
        lua_setfield(L, -2, "vers\xC3\xA3o");
    }

    /* 2) Headers */
    lua_newtable(L); /* req, headers */
    int headers_index = lua_gettop(L);
    int header_count = 0;
    int host_count = 0;

    while (p < end) {
        const char *hline_start = p;
        const char *hline_end = find_crlf(hline_start, end);
        if (!hline_end) {
            return http_parse_fail(L, "linha de cabe\xC3\xA7" "alho incompleta");
        }

        /* linha vazia? => fim dos headers */
        if (hline_start == hline_end || (hline_end == hline_start + 1 && (*hline_start == '\r' || *hline_start == '\n'))) {
            if (*hline_end == '\r' && hline_end + 1 < end && hline_end[1] == '\n')
                p = hline_end + 2;
            else
                p = hline_end + 1;
            break;
        }

        /* header: "Nome: valor" */
        if (*hline_start == ' ' || *hline_start == '\t')
            return http_parse_fail(L, "continua\xC3\xA7\xC3\xA3o de cabe\xC3\xA7" "alho n\xC3\xA3o \xC3\xA9 aceita");
        const char *colon = hline_start;
        for (; colon < hline_end && *colon != ':'; colon++);

        if (colon >= hline_end)
            return http_parse_fail(L, "cabe\xC3\xA7" "alho sem dois-pontos");
        {
            const char *name_start = hline_start;
            const char *name_end = colon;

            const char *val_start = colon + 1;
            const char *val_end = hline_end;

            trim_ascii(&name_start, &name_end);
            trim_ascii(&val_start, &val_end);

            if (!header_name_valid(name_start, (size_t)(name_end - name_start)))
                return http_parse_fail(L, "nome de cabe\xC3\xA7" "alho inv\xC3\xA1lido");
            if (!header_value_valid(val_start, (size_t)(val_end - val_start)))
                return http_parse_fail(L, "valor de cabe\xC3\xA7" "alho inv\xC3\xA1lido");
            header_count++;
            if (header_count > 100)
                return http_parse_fail(L, "quantidade de cabe\xC3\xA7" "alhos excede o limite");
            if (ascii_header_name_equal(name_start, name_end, "Host")) {
                host_count++;
                if (host_count > 1)
                    return http_parse_fail(L, "cabe\xC3\xA7" "alho Host repetido");
            }

            if (name_end > name_start) {
                char *name = g_strndup(name_start, (gsize)(name_end - name_start));
                lowercase_ascii(name);
                lua_pushstring(L, name); /* chave */
                g_free(name);

                lua_pushlstring(L, val_start, (size_t)(val_end - val_start)); /* valor */
                lua_settable(L, headers_index); /* headers[name] = valor */
            }
        }

        if (*hline_end == '\r' && hline_end + 1 < end && hline_end[1] == '\n')
            p = hline_end + 2;
        else
            p = hline_end + 1;
    }

    if (is_http11 && host_count != 1)
        return http_parse_fail(L, "HTTP/1.1 exige exatamente um cabe\xC3\xA7" "alho Host");

    /* cabeçalho */
    lua_setfield(L, -2, "cabe\xC3\xA7" "alho"); /* req.headers = headers */

    /* 3) Corpo: resto do buffer */
    if (p < end) {
        lua_pushlstring(L, p, (size_t)(end - p));
        lua_setfield(L, -2, "corpo");
    } else {
        lua_pushstring(L, "");
        lua_setfield(L, -2, "corpo");
    }

    /* sucesso: retorna req */
    return 1;
}

/* ---------------- registration ---------------- */

static const luaL_Reg pclient_methods[] = {
    /* conecteAssíncrono */
    {"conecteAss\xC3\xADncrono", l_client_connect_async},
    {"definaTempoLimite", l_client_set_timeout},
    {"cancele", l_client_cancel},
    {"feche", l_client_close},

    /* TLS */
    {"definaTLS", l_client_set_tls},
    {"definaValida\xC3\xA7\xC3\xA3oTLS", l_client_set_tls_validation},

    {NULL, NULL}
};

static const luaL_Reg pserver_methods[] = {
    {"amarre", l_server_bind},
    {"aceiteAss\xC3\xADncrono", l_server_accept_async},
    {"definaTempoLimite", l_server_set_timeout},
    {"cancele", l_server_cancel},
    {"feche", l_server_close},
    {NULL, NULL}
};

static const luaL_Reg pconn_methods[] = {
    {"envieAss\xC3\xADncrono", l_conn_send_async},
    {"recebaAss\xC3\xADncrono", l_conn_recv_async},
    {"recebaHTTPAss\xC3\xADncrono", l_conn_recv_async},
    {"recebaDadosAss\xC3\xADncrono", l_conn_recv_data_async},
    {"definaTempoLimite", l_conn_set_timeout},
    {"definaLimitesHTTP", l_conn_set_http_limits},
    {"cancele", l_conn_cancel},
    {"feche", l_conn_close},
    {NULL, NULL}
};

static const luaL_Reg pudp_methods[] = {
    {"amarre", l_udp_bind},
    {"enviePara", l_udp_sendto},
    {"envieParaAss\xC3\xADncrono", l_udp_sendto_async},
    {"inicieRecep\xC3\xA7\xC3\xA3o", l_udp_recv_start},
    {"pareRecep\xC3\xA7\xC3\xA3o", l_udp_recv_stop},
    {"definaTempoLimite", l_udp_set_timeout},
    {"cancele", l_udp_cancel},
    {"feche", l_udp_close},
    {NULL, NULL}
};

static const luaL_Reg rede_funcs[] = {
    {"clienteTCP", l_rede_tcp_cliente},
    {"servidorTCP", l_rede_tcp_servidor},
    {"udp", l_rede_udp},
    {"la\xC3\xA7o", l_rede_loop},
    {"pareLa\xC3\xA7o", l_rede_stop_loop},
    {"analiseHTTP", l_rede_analiseHTTP},
    {"respostaHTTP", l_rede_http_resposta},
    {"novaResposta", l_rede_nova_res},
    {NULL, NULL}
};


int luaopen_rede(lua_State *L) {
    /* metatable rede{cliente} */
    if (luaL_newmetatable(L, "rede{cliente}")) {
        luaL_setfuncs(L, pclient_methods, 0);
        lua_pushcfunction(L, l_client_gc); lua_setfield(L, -2, LUA_MM_FINALIZE);
        lua_pushvalue(L, -1); lua_setfield(L, -2, LUA_MM_INDICE);
    }
    lua_pop(L,1);

    /* metatable rede{servidor} */
    if (luaL_newmetatable(L, "rede{servidor}")) {
        luaL_setfuncs(L, pserver_methods, 0);
        lua_pushcfunction(L, l_server_gc); lua_setfield(L, -2, LUA_MM_FINALIZE);
        lua_pushvalue(L, -1); lua_setfield(L, -2, LUA_MM_INDICE);
    }
    lua_pop(L,1);

    /* metatable rede{conexão} */
    if (luaL_newmetatable(L, "rede{conex\xC3\xA3o}")) {
        luaL_setfuncs(L, pconn_methods, 0);
        lua_pushcfunction(L, l_conn_gc); lua_setfield(L, -2, LUA_MM_FINALIZE);
        lua_pushvalue(L, -1); lua_setfield(L, -2, LUA_MM_INDICE);
    }
    lua_pop(L,1);

    /* metatable rede{udp} */
    if (luaL_newmetatable(L, "rede{udp}")) {
        luaL_setfuncs(L, pudp_methods, 0);
        lua_pushcfunction(L, l_udp_gc); lua_setfield(L, -2, LUA_MM_FINALIZE);
        lua_pushvalue(L, -1); lua_setfield(L, -2, LUA_MM_INDICE);
    }
    lua_pop(L,1);
    /* metatable rede{res} */
    if (luaL_newmetatable(L, "rede{res}")) {
        static const luaL_Reg m[] = {
            {"c\xC3\xB3" "digo", l_res_status},
            {"definaCabe\xC3\xA7" "alho", l_res_set_header},
            {"envie", l_res_enviar},
            {"html", l_res_html},
            {"texto", l_res_texto},
            {"json", l_res_json},
            {NULL, NULL}
        };
        luaL_setfuncs(L, m, 0);
        lua_pushcfunction(L, l_res_gc);
        lua_setfield(L, -2, LUA_MM_FINALIZE);
        lua_pushvalue(L, -1);
        lua_setfield(L, -2, LUA_MM_INDICE);
    }
    lua_pop(L,1);

    luaL_newlib(L, rede_funcs);
    return 1;
}
