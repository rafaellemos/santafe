/**
 * mariadb.c (v3.0 - assíncrono, consultas preparadas e piscina nativa)
 *
 * - v2.1: CORREÇÃO CRÍTICA: Callbacks agora recriam o GSource se a operação continuar.
 * Isso é necessário porque se o status mudar de WAIT_WRITE para WAIT_READ,
 * o GSource antigo estaria ouvindo o evento errado.
 * - v3.0: consultas comuns e preparadas inteiramente não bloqueantes,
 *   piscina com fila/sessões e transações assíncronas.
 */

#define _GNU_SOURCE
#include <gio/gio.h>
#include <glib.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <limits.h>

#include <mysql.h>

#include "lua.h"
#include "lauxlib.h"

/* Adaptação dos helpers antigos (Prisma) para Santafé/Lua puro */
#define p_pushnil(L)           lua_pushnil((L))
#define p_pushstring(L, s)     lua_pushstring((L), (s))

#if defined(MARIADB_DEBUG)
#define DBG(fmt, ...) fprintf(stderr, "[MYSQL-C] " fmt "\n", ##__VA_ARGS__)
#else
#define DBG(...) ((void)0)
#endif


/* ---------------- 1. Tipos ---------------- */

typedef struct {
    MYSQL   *con;
    gboolean closed;
    gboolean busy;
    unsigned int open_statements;
    unsigned int open_results;
} ps_mysql_t;

typedef struct ps_mysql_stmt_s ps_mysql_stmt_t;

typedef enum {
    PS_RESULT_QUERY,
    PS_RESULT_STMT
} ps_result_kind_t;

typedef struct {
    MYSQL_BIND bind;
    char *buffer;
    unsigned long length;
    my_bool is_null;
    my_bool error;
} ps_stmt_column_t;

typedef struct {
    ps_result_kind_t kind;
    MYSQL_RES *res;
    MYSQL_STMT *stmt;
    ps_mysql_stmt_t *owner;
    int owner_ref;
    ps_mysql_t *connection;
    int connection_ref;
    int scope_ref;
    ps_stmt_column_t *columns;
    MYSQL_BIND *stmt_binds;
    int        num_fields;
    gboolean   closed;
    my_ulonglong affected_rows;
    my_ulonglong insert_id;
    void (*close_hook)(lua_State *L, void *data);
    void *close_hook_data;
} ps_mysql_res_t;

struct ps_mysql_stmt_s {
    MYSQL_STMT *stmt;
    ps_mysql_t *connection;
    int connection_ref;
    gboolean closed;
    gboolean busy;
    gboolean auto_close;
    int lease_ref;
};

typedef struct {
    MYSQL_BIND bind;
    char *string_value;
    unsigned long length;
    my_bool is_null;
    signed char boolean_value;
    long long integer_value;
    double number_value;
} ps_stmt_param_t;

typedef enum {
    QUERY_PHASE_EXECUTE,
    QUERY_PHASE_STORE
} query_phase_t;

/* Contexto de query assíncrona */
typedef struct {
    int        cb_ref;
    int        self_ref;
    lua_State *L;
    MYSQL     *con;
    ps_mysql_t *connection;
    int        wait_status;
    int        result_code;
    char      *query_str;
    size_t     query_len;
    query_phase_t phase;
    MYSQL_RES *result;
    guint      io_source;
    guint      timeout_source;
} async_ctx_t;

typedef enum {
    STMT_PHASE_PREPARE,
    STMT_PHASE_EXECUTE,
    STMT_PHASE_STORE
} stmt_phase_t;

typedef struct {
    lua_State *L;
    ps_mysql_t *connection;
    ps_mysql_stmt_t *statement;
    MYSQL *con;
    MYSQL_STMT *stmt;
    stmt_phase_t phase;
    gboolean prepare_only;
    int cb_ref;
    int con_ref;
    int stmt_ref;
    int params_ref;
    int wait_status;
    int result_code;
    guint io_source;
    guint timeout_source;
    char *sql;
    size_t sql_len;
    ps_stmt_param_t *params;
    MYSQL_BIND *param_binds;
    unsigned long param_count;
} stmt_async_ctx_t;

/* Contexto de conexão assíncrona */
typedef struct {
    int        cb_ref;
    lua_State *L;
    MYSQL     *con;
    MYSQL     *ret_con;
    int        wait_status;
    guint      io_source;
    guint      timeout_source;
    char *host; char *user; char *pass; char *db; char *unix_socket;
} connect_ctx_t;

/* ---------------- Piscina de conexões ---------------- */

typedef struct ps_mysql_pool_s ps_mysql_pool_t;

typedef enum {
    POOL_ENTRY_EMPTY,
    POOL_ENTRY_CONNECTING,
    POOL_ENTRY_FREE,
    POOL_ENTRY_OPERATION,
    POOL_ENTRY_SESSION,
    POOL_ENTRY_TRANSACTION,
    POOL_ENTRY_DEAD
} pool_entry_state_t;

typedef struct {
    ps_mysql_pool_t *pool;
    pool_entry_state_t state;
    ps_mysql_t *connection;
    int connection_ref;
    unsigned long generation;
} pool_entry_t;

typedef enum {
    POOL_JOB_ACQUIRE,
    POOL_JOB_EXECUTE,
    POOL_JOB_EXECUTE_PREPARED,
    POOL_JOB_BEGIN
} pool_job_kind_t;

typedef struct pool_job_s {
    ps_mysql_pool_t *pool;
    pool_job_kind_t kind;
    int callback_ref;
    int pool_ref;
    int params_ref;
    char *sql;
    size_t sql_len;
    guint timeout_source;
    gboolean queued;
} pool_job_t;

typedef struct {
    ps_mysql_pool_t *pool;
    pool_entry_t *entry;
    int pool_ref;
    gboolean active;
    gboolean transaction;
    unsigned long generation;
} ps_mysql_session_t;

typedef enum {
    POOL_OP_EXECUTE,
    POOL_OP_EXECUTE_PREPARED,
    POOL_OP_PREPARE,
    POOL_OP_BEGIN,
    POOL_OP_COMMIT,
    POOL_OP_ROLLBACK
} pool_op_kind_t;

typedef struct pool_op_s {
    lua_State *L;
    ps_mysql_pool_t *pool;
    pool_entry_t *entry;
    pool_op_kind_t kind;
    int callback_ref;
    int scope_ref;
    int params_ref;
    char *sql;
    size_t sql_len;
    gboolean release_after;
    gboolean dispatching;
    gboolean completed;
} pool_op_t;

typedef struct {
    lua_State *L;
    ps_mysql_pool_t *pool;
    pool_entry_t *entry;
    int pool_ref;
    gboolean initial;
    gboolean dispatching;
    gboolean completed;
} pool_connect_attempt_t;

typedef struct {
    ps_mysql_pool_t *pool;
    pool_entry_t *entry;
    int pool_ref;
} pool_result_lease_t;

struct ps_mysql_pool_s {
    lua_State *L;
    gboolean closed;
    gboolean initializing;
    gboolean ready;
    int minimum;
    int maximum;
    int max_queue;
    guint wait_ms;
    int initial_pending;
    int initial_callback_ref;
    char *initial_error;
    char *host;
    char *user;
    char *password;
    char *database;
    unsigned int port;
    pool_entry_t *entries;
    GQueue *queue;
};

/* ---------------- 2. Helpers ---------------- */

static int push_nil_err(lua_State *L, const char *msg) {
    p_pushnil(L);
    p_pushstring(L, msg ? msg : "erro");
    return 2;
}

/* Preserva todos os bits dos contadores do MariaDB. O inteiro do Santafé é
 * assinado; valores maiores que seu limite seguem como algarismos em um colar. */
static void push_mysql_uint(lua_State *L, my_ulonglong value) {
    if (value <= (my_ulonglong)LUA_MAXINTEGER) {
        lua_pushinteger(L, (lua_Integer)value);
    } else {
        char text[32];
        snprintf(text, sizeof(text), "%llu", (unsigned long long)value);
        lua_pushstring(L, text);
    }
}

static int store_callback(lua_State *L, int func_idx, int dado_idx) {
    lua_newtable(L);
    lua_pushvalue(L, func_idx);
    lua_setfield(L, -2, "func");
    if (lua_isnoneornil(L, dado_idx)) { lua_pushnil(L); } else { lua_pushvalue(L, dado_idx); }
    lua_setfield(L, -2, "dado");
    return luaL_ref(L, LUA_REGISTRYINDEX);
}

static async_ctx_t* create_async_ctx(lua_State *L, int func_idx, int dado_idx) {
    async_ctx_t *ctx = g_new0(async_ctx_t, 1);
    ctx->L = L;
    lua_pushvalue(L, 1);
    ctx->self_ref = luaL_ref(L, LUA_REGISTRYINDEX);
    ctx->cb_ref = store_callback(L, func_idx, dado_idx);
    ctx->wait_status = 0;
    ctx->result_code = 0;
    ctx->phase = QUERY_PHASE_EXECUTE;
    return ctx;
}

static void clear_async_sources(async_ctx_t *ctx) {
    if (!ctx) return;
    if (ctx->io_source) {
        g_source_remove(ctx->io_source);
        ctx->io_source = 0;
    }
    if (ctx->timeout_source) {
        g_source_remove(ctx->timeout_source);
        ctx->timeout_source = 0;
    }
}

static void free_async_ctx(async_ctx_t *ctx) {
    if (!ctx) return;
    clear_async_sources(ctx);
    if (ctx->cb_ref   != LUA_NOREF) luaL_unref(ctx->L, LUA_REGISTRYINDEX, ctx->cb_ref);
    if (ctx->self_ref != LUA_NOREF) luaL_unref(ctx->L, LUA_REGISTRYINDEX, ctx->self_ref);
    if (ctx->query_str) g_free(ctx->query_str);
    g_free(ctx);
}

static connect_ctx_t* create_connect_ctx(lua_State *L, int func_idx, int dado_idx) {
    connect_ctx_t *ctx = g_new0(connect_ctx_t, 1);
    ctx->L = L;
    ctx->cb_ref = store_callback(L, func_idx, dado_idx);
    return ctx;
}

static void clear_connect_sources(connect_ctx_t *ctx) {
    if (!ctx) return;
    if (ctx->io_source) {
        g_source_remove(ctx->io_source);
        ctx->io_source = 0;
    }
    if (ctx->timeout_source) {
        g_source_remove(ctx->timeout_source);
        ctx->timeout_source = 0;
    }
}

static void free_connect_ctx(connect_ctx_t *ctx) {
    if (!ctx) return;
    clear_connect_sources(ctx);
    if (ctx->cb_ref != LUA_NOREF) luaL_unref(ctx->L, LUA_REGISTRYINDEX, ctx->cb_ref);
    if (ctx->host) g_free(ctx->host);
    if (ctx->user) g_free(ctx->user);
    if (ctx->pass) g_free(ctx->pass);
    if (ctx->db)   g_free(ctx->db);
    if (ctx->unix_socket) g_free(ctx->unix_socket);
    g_free(ctx);
}



/* ---------------- 3. Construtores / Checkers ---------------- */

#define PS_MYSQL_CON "mariadb{conex\xC3\xA3o}"
#define PS_MYSQL_RES "mariadb{resultado}"
#define PS_MYSQL_STMT "mariadb{consultaPreparada}"
#define PS_MYSQL_POOL "mariadb{piscina}"
#define PS_MYSQL_SESSION "mariadb{sess\xC3\xA3o}"
#define PS_MYSQL_TRANSACTION "mariadb{transa\xC3\xA7\xC3\xA3o}"


static ps_mysql_t* push_new_pcon(lua_State *L, MYSQL *con) {
    ps_mysql_t *ud = (ps_mysql_t*)lua_newuserdata(L, sizeof(ps_mysql_t));
    memset(ud, 0, sizeof(*ud));
    ud->con = con;
    ud->closed = (con == NULL);
    ud->busy = FALSE;
    ud->open_statements = 0;
    ud->open_results = 0;
    luaL_getmetatable(L, PS_MYSQL_CON);
    lua_setmetatable(L, -2);
    return ud;
}

static ps_mysql_res_t* push_new_pres(lua_State *L, MYSQL_RES *res, MYSQL *con,
                                     ps_mysql_t *connection,
                                     int connection_ref) {
    ps_mysql_res_t *ud = (ps_mysql_res_t*)lua_newuserdata(L, sizeof(ps_mysql_res_t));
    memset(ud, 0, sizeof(*ud));
    ud->kind = PS_RESULT_QUERY;
    ud->res = res;
    ud->owner_ref = LUA_NOREF;
    ud->connection_ref = LUA_NOREF;
    ud->scope_ref = LUA_NOREF;
    ud->connection = connection;
    ud->closed = FALSE;
    if (res) { ud->num_fields = mysql_num_fields(res); }
    if (con) {
        ud->affected_rows = mysql_affected_rows(con);
        ud->insert_id = mysql_insert_id(con);
    }
    if (connection && connection_ref != LUA_NOREF) {
        lua_rawgeti(L, LUA_REGISTRYINDEX, connection_ref);
        ud->connection_ref = luaL_ref(L, LUA_REGISTRYINDEX);
        connection->open_results++;
    }
    luaL_getmetatable(L, PS_MYSQL_RES);
    lua_setmetatable(L, -2);
    return ud;
}

static ps_mysql_stmt_t* push_new_pstmt(lua_State *L, MYSQL_STMT *stmt,
                                       ps_mysql_t *connection,
                                       int connection_index,
                                       gboolean auto_close) {
    ps_mysql_stmt_t *ud = (ps_mysql_stmt_t*)lua_newuserdata(L, sizeof(ps_mysql_stmt_t));
    memset(ud, 0, sizeof(*ud));
    ud->stmt = stmt;
    ud->connection = connection;
    ud->closed = (stmt == NULL);
    ud->busy = FALSE;
    ud->auto_close = auto_close;
    ud->lease_ref = LUA_NOREF;
    lua_pushvalue(L, connection_index);
    ud->connection_ref = luaL_ref(L, LUA_REGISTRYINDEX);
    if (connection) connection->open_statements++;
    luaL_getmetatable(L, PS_MYSQL_STMT);
    lua_setmetatable(L, -2);
    return ud;
}

static ps_mysql_t* check_pcon(lua_State *L, int idx) { return (ps_mysql_t*)luaL_checkudata(L, idx, PS_MYSQL_CON); }
static ps_mysql_res_t* check_pres(lua_State *L, int idx) { return (ps_mysql_res_t*)luaL_checkudata(L, idx, PS_MYSQL_RES); }
static ps_mysql_stmt_t* check_pstmt(lua_State *L, int idx) { return (ps_mysql_stmt_t*)luaL_checkudata(L, idx, PS_MYSQL_STMT); }

static void close_pstmt(lua_State *L, ps_mysql_stmt_t *ud) {
    if (!ud || ud->closed) return;
    if (ud->stmt) mysql_stmt_close(ud->stmt);
    ud->stmt = NULL;
    ud->closed = TRUE;
    ud->busy = FALSE;
    if (ud->connection && ud->connection->open_statements > 0)
        ud->connection->open_statements--;
    if (ud->connection_ref != LUA_NOREF) {
        luaL_unref(L, LUA_REGISTRYINDEX, ud->connection_ref);
        ud->connection_ref = LUA_NOREF;
    }
    if (ud->lease_ref != LUA_NOREF) {
        luaL_unref(L, LUA_REGISTRYINDEX, ud->lease_ref);
        ud->lease_ref = LUA_NOREF;
    }
    ud->connection = NULL;
}

static int l_mysql_close(lua_State *L) {
    ps_mysql_t *ud = check_pcon(L, 1);
    if (ud->closed) return 0;
    if (ud->busy) return push_nil_err(L, "conex\xC3\xA3o MariaDB ocupada");
    if (ud->open_statements > 0)
        return push_nil_err(L, "feche as consultas preparadas antes da conex\xC3\xA3o");
    if (ud->open_results > 0)
        return push_nil_err(L, "feche os resultados antes da conex\xC3\xA3o");
    mysql_close(ud->con);
    ud->con = NULL;
    ud->closed = TRUE;
    return 0;
}

static int l_mysql_gc(lua_State *L) {
    ps_mysql_t *ud = check_pcon(L, 1);
    if (!ud->closed && ud->open_statements == 0 && ud->open_results == 0) {
        mysql_close(ud->con);
        ud->con = NULL;
        ud->closed = TRUE;
    }
    return 0;
}

static int l_stmt_close(lua_State *L) {
    ps_mysql_stmt_t *ud = check_pstmt(L, 1);
    if (ud->closed) return 0;
    if (ud->busy)
        return push_nil_err(L, "a consulta preparada ainda est\xC3\xA1 em uso");
    close_pstmt(L, ud);
    return 0;
}

static int l_stmt_gc(lua_State *L) {
    ps_mysql_stmt_t *ud = check_pstmt(L, 1);
    if (!ud->busy) close_pstmt(L, ud);
    return 0;
}

static void free_stmt_columns(ps_mysql_res_t *ud) {
    if (!ud) return;
    if (ud->columns) {
        for (int i = 0; i < ud->num_fields; i++) g_free(ud->columns[i].buffer);
        g_free(ud->columns);
    }
    g_free(ud->stmt_binds);
    ud->columns = NULL;
    ud->stmt_binds = NULL;
}

static int l_res_close(lua_State *L) {
    ps_mysql_res_t *ud = check_pres(L, 1);
    if (ud->closed) return 0;
    if (ud->kind == PS_RESULT_QUERY) {
        if (ud->res) mysql_free_result(ud->res);
        if (ud->connection && ud->connection->open_results > 0)
            ud->connection->open_results--;
    } else {
        if (ud->stmt) mysql_stmt_free_result(ud->stmt);
        free_stmt_columns(ud);
        if (ud->owner) {
            ud->owner->busy = FALSE;
            if (ud->owner->auto_close) close_pstmt(L, ud->owner);
        }
        if (ud->owner_ref != LUA_NOREF) {
            luaL_unref(L, LUA_REGISTRYINDEX, ud->owner_ref);
            ud->owner_ref = LUA_NOREF;
        }
    }
    ud->res = NULL;
    ud->stmt = NULL;
    ud->owner = NULL;
    ud->connection = NULL;
    ud->closed = TRUE;
    if (ud->connection_ref != LUA_NOREF) {
        luaL_unref(L, LUA_REGISTRYINDEX, ud->connection_ref);
        ud->connection_ref = LUA_NOREF;
    }
    if (ud->scope_ref != LUA_NOREF) {
        luaL_unref(L, LUA_REGISTRYINDEX, ud->scope_ref);
        ud->scope_ref = LUA_NOREF;
    }
    if (ud->close_hook) {
        void (*hook)(lua_State*, void*) = ud->close_hook;
        void *data = ud->close_hook_data;
        ud->close_hook = NULL;
        ud->close_hook_data = NULL;
        hook(L, data);
    }
    return 0;
}

/* ---------------- 4. Callbacks Assíncronos (LÓGICA ROBUSTA) ---------------- */

static void continue_query_operation(async_ctx_t *ctx, int event_status);

static void push_exec_callback_args(lua_State *L, async_ctx_t *ctx, MYSQL_RES *res, const char *err_msg) {
    lua_rawgeti(L, LUA_REGISTRYINDEX, ctx->cb_ref);
    lua_getfield(L, -1, "func");
    lua_remove(L, -2);
    lua_rawgeti(L, LUA_REGISTRYINDEX, ctx->self_ref);

    if (err_msg) {
        lua_pushnil(L);
        lua_pushstring(L, err_msg);
    } else {
        push_new_pres(L, res, ctx->con, ctx->connection, ctx->self_ref);
        lua_pushnil(L);
    }

    lua_rawgeti(L, LUA_REGISTRYINDEX, ctx->cb_ref);
    lua_getfield(L, -1, "dado");
    lua_remove(L, -2);
}

static void finish_query(async_ctx_t *ctx, const char *err_msg) {
    lua_State *L = ctx->L;
    char fallback[128];
    if (err_msg && err_msg[0] == '\0') err_msg = NULL;
    if (!err_msg && ctx->result_code != 0) {
        unsigned int eno = mysql_errno(ctx->con);
        snprintf(fallback, sizeof(fallback),
                 "c\xC3\xB3" "digo de erro da consulta MariaDB %u", eno);
        err_msg = fallback;
    }
    if (ctx->connection) ctx->connection->busy = FALSE;
    push_exec_callback_args(L, ctx, ctx->result, err_msg);
    ctx->result = NULL; /* o userdata passou a ser o dono */
    if (lua_pcall(L, 4, 0, 0) != 0) {
        const char *e = lua_tostring(L, -1);
        g_printerr("executeAss\xC3\xADncrono retornou erro: %s\n",
                   e ? e : "<erro>");
        lua_pop(L, 1);
    }
    free_async_ctx(ctx);
}

static void schedule_query_wait(async_ctx_t *ctx);

static void start_query_store(async_ctx_t *ctx) {
    ctx->phase = QUERY_PHASE_STORE;
    ctx->result = NULL;
    ctx->wait_status = mysql_store_result_start(&ctx->result, ctx->con);
    if (ctx->wait_status) {
        schedule_query_wait(ctx);
    } else if (!ctx->result && mysql_field_count(ctx->con) != 0) {
        finish_query(ctx, mysql_error(ctx->con));
    } else {
        finish_query(ctx, NULL);
    }
}

static void continue_query_operation(async_ctx_t *ctx, int event_status) {
    if (ctx->phase == QUERY_PHASE_EXECUTE) {
        ctx->wait_status = mysql_real_query_cont(&ctx->result_code,
                                                 ctx->con,
                                                 event_status);
    } else {
        ctx->wait_status = mysql_store_result_cont(&ctx->result,
                                                   ctx->con,
                                                   event_status);
    }
    if (ctx->wait_status) {
        schedule_query_wait(ctx);
        return;
    }
    if (ctx->phase == QUERY_PHASE_EXECUTE) {
        if (ctx->result_code != 0) {
            finish_query(ctx, mysql_error(ctx->con));
        } else if (mysql_field_count(ctx->con) != 0) {
            start_query_store(ctx);
        } else {
            finish_query(ctx, NULL);
        }
    } else if (!ctx->result && mysql_field_count(ctx->con) != 0) {
        finish_query(ctx, mysql_error(ctx->con));
    } else {
        finish_query(ctx, NULL);
    }
}

static gboolean query_io_cb(GIOChannel *source, GIOCondition condition,
                             gpointer user_data) {
    async_ctx_t *ctx = (async_ctx_t*)user_data;
    int event_status = 0;
    (void)source;
    ctx->io_source = 0;
    if (ctx->timeout_source) {
        g_source_remove(ctx->timeout_source);
        ctx->timeout_source = 0;
    }
    if (condition & G_IO_IN) event_status |= MYSQL_WAIT_READ;
    if (condition & G_IO_OUT) event_status |= MYSQL_WAIT_WRITE;
    if (condition & G_IO_PRI) event_status |= MYSQL_WAIT_EXCEPT;
    continue_query_operation(ctx, event_status);
    return G_SOURCE_REMOVE;
}

static gboolean query_timeout_cb(gpointer user_data) {
    async_ctx_t *ctx = (async_ctx_t*)user_data;
    ctx->timeout_source = 0;
    if (ctx->io_source) {
        g_source_remove(ctx->io_source);
        ctx->io_source = 0;
    }
    continue_query_operation(ctx, MYSQL_WAIT_TIMEOUT);
    return G_SOURCE_REMOVE;
}

static void schedule_query_wait(async_ctx_t *ctx) {
    GIOCondition condition = G_IO_ERR | G_IO_HUP | G_IO_NVAL;
    if (ctx->wait_status & MYSQL_WAIT_READ) condition |= G_IO_IN;
    if (ctx->wait_status & MYSQL_WAIT_WRITE) condition |= G_IO_OUT;
    if (ctx->wait_status & MYSQL_WAIT_EXCEPT) condition |= G_IO_PRI;
    if (ctx->wait_status &
        (MYSQL_WAIT_READ | MYSQL_WAIT_WRITE | MYSQL_WAIT_EXCEPT)) {
        int fd = mysql_get_socket(ctx->con);
        GIOChannel *channel = g_io_channel_unix_new(fd);
        ctx->io_source = g_io_add_watch(channel, condition, query_io_cb, ctx);
        g_io_channel_unref(channel);
    }
    if (ctx->wait_status & MYSQL_WAIT_TIMEOUT) {
        unsigned int timeout_ms = mysql_get_timeout_value_ms(ctx->con);
        if (timeout_ms == 0) timeout_ms = 1;
        ctx->timeout_source = g_timeout_add(timeout_ms, query_timeout_cb, ctx);
    }
    if (!ctx->io_source && !ctx->timeout_source)
        ctx->timeout_source = g_timeout_add(1, query_timeout_cb, ctx);
}

/* --- CONNECT CALLBACK --- */

static void continue_connect_operation(connect_ctx_t *ctx, int event_status);

static void push_connect_callback_args(lua_State *L, connect_ctx_t *ctx, MYSQL *ret_con, const char *err_msg) {
    lua_rawgeti(L, LUA_REGISTRYINDEX, ctx->cb_ref);
    lua_getfield(L, -1, "func");
    lua_remove(L, -2);

    if (ret_con == NULL) {
        lua_pushnil(L);
        lua_pushstring(L, err_msg ? err_msg : "falha ao conectar");
    } else {
        push_new_pcon(L, ret_con);
        lua_pushnil(L);
    }

    lua_rawgeti(L, LUA_REGISTRYINDEX, ctx->cb_ref);
    lua_getfield(L, -1, "dado");
    lua_remove(L, -2);
}

static void finish_connect(connect_ctx_t *ctx) {
    lua_State *L = ctx->L;
    char *error_copy = NULL;
    if (!ctx->ret_con) {
        const char *message = mysql_error(ctx->con);
        error_copy = g_strdup(message && message[0] ? message
                                                   : "falha ao conectar");
        mysql_close(ctx->con);
        ctx->con = NULL;
    }
    push_connect_callback_args(L, ctx, ctx->ret_con, error_copy);
    if (lua_pcall(L, 3, 0, 0) != 0) {
        const char *e = lua_tostring(L, -1);
        g_printerr("conecteAss\xC3\xADncrono retornou erro: %s\n",
                   e ? e : "<erro>");
        lua_pop(L, 1);
    }
    g_free(error_copy);
    free_connect_ctx(ctx);
}

static gboolean connect_io_cb(GIOChannel *source, GIOCondition condition,
                               gpointer user_data) {
    connect_ctx_t *ctx = (connect_ctx_t*)user_data;
    int event_status = 0;
    (void)source;
    ctx->io_source = 0;
    if (ctx->timeout_source) {
        g_source_remove(ctx->timeout_source);
        ctx->timeout_source = 0;
    }
    if (condition & G_IO_IN) event_status |= MYSQL_WAIT_READ;
    if (condition & G_IO_OUT) event_status |= MYSQL_WAIT_WRITE;
    if (condition & G_IO_PRI) event_status |= MYSQL_WAIT_EXCEPT;
    continue_connect_operation(ctx, event_status);
    return G_SOURCE_REMOVE;
}

static gboolean connect_timeout_cb(gpointer user_data) {
    connect_ctx_t *ctx = (connect_ctx_t*)user_data;
    ctx->timeout_source = 0;
    if (ctx->io_source) {
        g_source_remove(ctx->io_source);
        ctx->io_source = 0;
    }
    continue_connect_operation(ctx, MYSQL_WAIT_TIMEOUT);
    return G_SOURCE_REMOVE;
}

static void schedule_connect_wait(connect_ctx_t *ctx) {
    GIOCondition condition = G_IO_ERR | G_IO_HUP | G_IO_NVAL;
    if (ctx->wait_status & MYSQL_WAIT_READ) condition |= G_IO_IN;
    if (ctx->wait_status & MYSQL_WAIT_WRITE) condition |= G_IO_OUT;
    if (ctx->wait_status & MYSQL_WAIT_EXCEPT) condition |= G_IO_PRI;
    if (ctx->wait_status &
        (MYSQL_WAIT_READ | MYSQL_WAIT_WRITE | MYSQL_WAIT_EXCEPT)) {
        int fd = mysql_get_socket(ctx->con);
        GIOChannel *channel = g_io_channel_unix_new(fd);
        ctx->io_source = g_io_add_watch(channel, condition, connect_io_cb, ctx);
        g_io_channel_unref(channel);
    }
    if (ctx->wait_status & MYSQL_WAIT_TIMEOUT) {
        unsigned int timeout_ms = mysql_get_timeout_value_ms(ctx->con);
        if (timeout_ms == 0) timeout_ms = 1;
        ctx->timeout_source = g_timeout_add(timeout_ms, connect_timeout_cb, ctx);
    }
    if (!ctx->io_source && !ctx->timeout_source)
        ctx->timeout_source = g_timeout_add(1, connect_timeout_cb, ctx);
}

static void continue_connect_operation(connect_ctx_t *ctx, int event_status) {
    ctx->wait_status = mysql_real_connect_cont(&ctx->ret_con,
                                               ctx->con,
                                               event_status);
    DBG("connect_cont: wait_status=%d", ctx->wait_status);
    if (ctx->wait_status) schedule_connect_wait(ctx);
    else finish_connect(ctx);
}

/* ---------------- 5. Consultas preparadas assíncronas ---------------- */

static void free_stmt_params(stmt_async_ctx_t *ctx) {
    if (!ctx || !ctx->params) return;
    for (unsigned long i = 0; i < ctx->param_count; i++)
        g_free(ctx->params[i].string_value);
    g_free(ctx->params);
    g_free(ctx->param_binds);
    ctx->params = NULL;
    ctx->param_binds = NULL;
    ctx->param_count = 0;
}

static void clear_stmt_sources(stmt_async_ctx_t *ctx) {
    if (ctx->io_source) {
        g_source_remove(ctx->io_source);
        ctx->io_source = 0;
    }
    if (ctx->timeout_source) {
        g_source_remove(ctx->timeout_source);
        ctx->timeout_source = 0;
    }
}

static void free_stmt_ctx(stmt_async_ctx_t *ctx) {
    if (!ctx) return;
    clear_stmt_sources(ctx);
    free_stmt_params(ctx);
    if (ctx->cb_ref != LUA_NOREF)
        luaL_unref(ctx->L, LUA_REGISTRYINDEX, ctx->cb_ref);
    if (ctx->con_ref != LUA_NOREF)
        luaL_unref(ctx->L, LUA_REGISTRYINDEX, ctx->con_ref);
    if (ctx->stmt_ref != LUA_NOREF)
        luaL_unref(ctx->L, LUA_REGISTRYINDEX, ctx->stmt_ref);
    if (ctx->params_ref != LUA_NOREF)
        luaL_unref(ctx->L, LUA_REGISTRYINDEX, ctx->params_ref);
    g_free(ctx->sql);
    g_free(ctx);
}

static stmt_async_ctx_t *new_stmt_ctx(lua_State *L, int func_idx, int dado_idx) {
    stmt_async_ctx_t *ctx = g_new0(stmt_async_ctx_t, 1);
    ctx->L = L;
    ctx->cb_ref = store_callback(L, func_idx, dado_idx);
    ctx->con_ref = LUA_NOREF;
    ctx->stmt_ref = LUA_NOREF;
    ctx->params_ref = LUA_NOREF;
    return ctx;
}

static int duplicate_registry_ref(lua_State *L, int ref) {
    lua_rawgeti(L, LUA_REGISTRYINDEX, ref);
    return luaL_ref(L, LUA_REGISTRYINDEX);
}

static gboolean bind_stmt_params(stmt_async_ctx_t *ctx, const char **err_msg) {
    lua_State *L = ctx->L;
    unsigned long expected = mysql_stmt_param_count(ctx->stmt);
    free_stmt_params(ctx);
    ctx->param_count = expected;

    lua_rawgeti(L, LUA_REGISTRYINDEX, ctx->params_ref);
    if (!lua_istable(L, -1)) {
        lua_pop(L, 1);
        *err_msg = "os par\xC3\xA2metros devem estar em uma tabela";
        return FALSE;
    }

    /* Aceita nulo como uma posição ausente, mas rejeita chaves que não
       correspondam a um marcador. Assim, um valor extra nunca é ignorado
       silenciosamente por causa do operador de tamanho de tabelas esparsas. */
    lua_pushnil(L);
    while (lua_next(L, -2) != 0) {
        lua_Integer index;
        if (!lua_isinteger(L, -2) ||
            (index = lua_tointeger(L, -2)) < 1 ||
            (lua_Unsigned)index > (lua_Unsigned)expected) {
            lua_pop(L, 3); /* valor, chave e tabela */
            *err_msg = "a tabela de par\xC3\xA2metros cont\xC3\xA9m uma posi\xC3\xA7\xC3\xA3o sem marcador correspondente";
            return FALSE;
        }
        lua_pop(L, 1); /* preserva a chave para lua_next */
    }

    if (expected == 0) {
        lua_pop(L, 1);
        return TRUE;
    }

    ctx->params = g_new0(ps_stmt_param_t, expected);
    ctx->param_binds = g_new0(MYSQL_BIND, expected);
    for (unsigned long i = 0; i < expected; i++) {
        ps_stmt_param_t *p = &ctx->params[i];
        MYSQL_BIND *b = &p->bind;
        lua_rawgeti(L, -1, (lua_Integer)i + 1);
        int type = lua_type(L, -1);

        b->is_null = &p->is_null;
        b->length = &p->length;

        if (type == LUA_TNIL ||
            (type == LUA_TLIGHTUSERDATA && lua_touserdata(L, -1) == NULL)) {
            p->is_null = 1;
            b->buffer_type = MYSQL_TYPE_NULL;
        } else if (type == LUA_TBOOLEAN) {
            p->boolean_value = (signed char)lua_toboolean(L, -1);
            p->length = sizeof(p->boolean_value);
            b->buffer_type = MYSQL_TYPE_TINY;
            b->buffer = &p->boolean_value;
            b->buffer_length = sizeof(p->boolean_value);
        } else if (lua_isinteger(L, -1)) {
            p->integer_value = (long long)lua_tointeger(L, -1);
            p->length = sizeof(p->integer_value);
            b->buffer_type = MYSQL_TYPE_LONGLONG;
            b->buffer = &p->integer_value;
            b->buffer_length = sizeof(p->integer_value);
        } else if (type == LUA_TNUMBER) {
            p->number_value = (double)lua_tonumber(L, -1);
            p->length = sizeof(p->number_value);
            b->buffer_type = MYSQL_TYPE_DOUBLE;
            b->buffer = &p->number_value;
            b->buffer_length = sizeof(p->number_value);
        } else if (type == LUA_TSTRING) {
            size_t len = 0;
            const char *value = lua_tolstring(L, -1, &len);
            if (len > ULONG_MAX) {
                lua_pop(L, 2);
                *err_msg = "par\xC3\xA2metro de colar grande demais";
                return FALSE;
            }
            p->string_value = g_memdup2(value, len ? len : 1);
            p->length = (unsigned long)len;
            b->buffer_type = MYSQL_TYPE_STRING;
            b->buffer = p->string_value;
            b->buffer_length = p->length;
        } else {
            static char type_error[160];
            snprintf(type_error, sizeof(type_error),
                     "tipo '%s' n\xC3\xA3o aceito no par\xC3\xA2metro %lu",
                     lua_typename(L, type), i + 1);
            lua_pop(L, 2);
            *err_msg = type_error;
            return FALSE;
        }
        ctx->param_binds[i] = *b;
        lua_pop(L, 1);
    }
    lua_pop(L, 1);

    if (mysql_stmt_bind_param(ctx->stmt, ctx->param_binds) != 0) {
        *err_msg = mysql_stmt_error(ctx->stmt);
        return FALSE;
    }
    return TRUE;
}

static ps_mysql_res_t *push_new_stmt_result(lua_State *L,
                                             stmt_async_ctx_t *ctx,
                                             const char **err_msg) {
    ps_mysql_res_t *ud = (ps_mysql_res_t*)lua_newuserdata(L, sizeof(ps_mysql_res_t));
    memset(ud, 0, sizeof(*ud));
    ud->kind = PS_RESULT_STMT;
    ud->stmt = ctx->stmt;
    ud->owner = ctx->statement;
    ud->owner_ref = LUA_NOREF;
    ud->connection_ref = LUA_NOREF;
    ud->scope_ref = LUA_NOREF;
    ud->closed = FALSE;
    ud->num_fields = (int)mysql_stmt_field_count(ctx->stmt);
    ud->affected_rows = mysql_stmt_affected_rows(ctx->stmt);
    ud->insert_id = mysql_stmt_insert_id(ctx->stmt);

    if (ud->num_fields > 0) {
        MYSQL_RES *meta = mysql_stmt_result_metadata(ctx->stmt);
        if (!meta) {
            *err_msg = mysql_stmt_error(ctx->stmt);
            lua_pop(L, 1);
            return NULL;
        }
        MYSQL_FIELD *fields = mysql_fetch_fields(meta);
        ud->columns = g_new0(ps_stmt_column_t, ud->num_fields);
        ud->stmt_binds = g_new0(MYSQL_BIND, ud->num_fields);
        for (int i = 0; i < ud->num_fields; i++) {
            ps_stmt_column_t *column = &ud->columns[i];
            unsigned long size = fields[i].max_length;
            if ((guint64)size > (guint64)G_MAXSIZE - 1) {
                mysql_free_result(meta);
                free_stmt_columns(ud);
                *err_msg = "coluna grande demais para ser armazenada";
                lua_pop(L, 1);
                return NULL;
            }
            column->buffer = g_malloc((gsize)size + 1);
            column->bind.buffer_type = MYSQL_TYPE_STRING;
            column->bind.buffer = column->buffer;
            column->bind.buffer_length = size + 1;
            column->bind.length = &column->length;
            column->bind.is_null = &column->is_null;
            column->bind.error = &column->error;
            ud->stmt_binds[i] = column->bind;
        }
        mysql_free_result(meta);
        if (mysql_stmt_bind_result(ctx->stmt, ud->stmt_binds) != 0) {
            *err_msg = mysql_stmt_error(ctx->stmt);
            free_stmt_columns(ud);
            lua_pop(L, 1);
            return NULL;
        }
    }

    ud->owner_ref = duplicate_registry_ref(L, ctx->stmt_ref);
    luaL_getmetatable(L, PS_MYSQL_RES);
    lua_setmetatable(L, -2);
    return ud;
}

static void push_stored_callback(lua_State *L, int cb_ref, const char *field) {
    lua_rawgeti(L, LUA_REGISTRYINDEX, cb_ref);
    lua_getfield(L, -1, field);
    lua_remove(L, -2);
}

static gboolean stmt_callback_uses_connection(stmt_async_ctx_t *ctx) {
    return ctx->prepare_only || ctx->statement->auto_close;
}

static void push_stmt_owner(stmt_async_ctx_t *ctx) {
    int ref = stmt_callback_uses_connection(ctx) ? ctx->con_ref : ctx->stmt_ref;
    lua_rawgeti(ctx->L, LUA_REGISTRYINDEX, ref);
}

static void finish_stmt_error(stmt_async_ctx_t *ctx, const char *err_msg) {
    lua_State *L = ctx->L;
    if (!err_msg || err_msg[0] == '\0') err_msg = "falha na consulta preparada";
    ctx->connection->busy = FALSE;
    ctx->statement->busy = FALSE;

    push_stored_callback(L, ctx->cb_ref, "func");
    push_stmt_owner(ctx);
    lua_pushnil(L);
    lua_pushstring(L, err_msg);
    push_stored_callback(L, ctx->cb_ref, "dado");

    if (ctx->prepare_only || ctx->statement->auto_close)
        close_pstmt(L, ctx->statement);

    if (lua_pcall(L, 4, 0, 0) != 0) {
        g_printerr("consulta preparada retornou erro: %s\n",
                   lua_tostring(L, -1));
        lua_pop(L, 1);
    }
    free_stmt_ctx(ctx);
}

static void finish_prepare_success(stmt_async_ctx_t *ctx) {
    lua_State *L = ctx->L;
    ctx->connection->busy = FALSE;
    ctx->statement->busy = FALSE;
    push_stored_callback(L, ctx->cb_ref, "func");
    lua_rawgeti(L, LUA_REGISTRYINDEX, ctx->con_ref);
    lua_rawgeti(L, LUA_REGISTRYINDEX, ctx->stmt_ref);
    lua_pushnil(L);
    push_stored_callback(L, ctx->cb_ref, "dado");
    if (lua_pcall(L, 4, 0, 0) != 0) {
        g_printerr("prepareConsultaAss\xC3\xADncrona retornou erro: %s\n",
                   lua_tostring(L, -1));
        lua_pop(L, 1);
    }
    free_stmt_ctx(ctx);
}

static void finish_execute_success(stmt_async_ctx_t *ctx) {
    lua_State *L = ctx->L;
    const char *err_msg = NULL;
    ps_mysql_res_t *result;
    ctx->connection->busy = FALSE;

    push_stored_callback(L, ctx->cb_ref, "func");
    push_stmt_owner(ctx);
    result = push_new_stmt_result(L, ctx, &err_msg);
    if (!result) {
        lua_pop(L, 2); /* dono e fun\xC3\xA7\xC3\xA3o */
        finish_stmt_error(ctx, err_msg);
        return;
    }
    lua_pushnil(L);
    push_stored_callback(L, ctx->cb_ref, "dado");
    if (lua_pcall(L, 4, 0, 0) != 0) {
        g_printerr("executeAss\xC3\xADncrono preparado retornou erro: %s\n",
                   lua_tostring(L, -1));
        lua_pop(L, 1);
    }
    free_stmt_ctx(ctx);
}

static void start_stmt_execute(stmt_async_ctx_t *ctx);
static void continue_stmt_operation(stmt_async_ctx_t *ctx, int event_status);

static gboolean stmt_io_cb(GIOChannel *source, GIOCondition condition,
                            gpointer user_data) {
    stmt_async_ctx_t *ctx = (stmt_async_ctx_t*)user_data;
    int event_status = 0;
    (void)source;
    ctx->io_source = 0;
    if (ctx->timeout_source) {
        g_source_remove(ctx->timeout_source);
        ctx->timeout_source = 0;
    }
    if (condition & G_IO_IN) event_status |= MYSQL_WAIT_READ;
    if (condition & G_IO_OUT) event_status |= MYSQL_WAIT_WRITE;
    if (condition & G_IO_PRI) event_status |= MYSQL_WAIT_EXCEPT;
    continue_stmt_operation(ctx, event_status);
    return G_SOURCE_REMOVE;
}

static gboolean stmt_timeout_cb(gpointer user_data) {
    stmt_async_ctx_t *ctx = (stmt_async_ctx_t*)user_data;
    ctx->timeout_source = 0;
    if (ctx->io_source) {
        g_source_remove(ctx->io_source);
        ctx->io_source = 0;
    }
    continue_stmt_operation(ctx, MYSQL_WAIT_TIMEOUT);
    return G_SOURCE_REMOVE;
}

static void schedule_stmt_wait(stmt_async_ctx_t *ctx) {
    int fd = mysql_get_socket(ctx->con);
    GIOCondition condition = G_IO_ERR | G_IO_HUP | G_IO_NVAL;
    if (ctx->wait_status & MYSQL_WAIT_READ) condition |= G_IO_IN;
    if (ctx->wait_status & MYSQL_WAIT_WRITE) condition |= G_IO_OUT;
    if (ctx->wait_status & MYSQL_WAIT_EXCEPT) condition |= G_IO_PRI;

    if (ctx->wait_status & (MYSQL_WAIT_READ | MYSQL_WAIT_WRITE | MYSQL_WAIT_EXCEPT)) {
        GIOChannel *channel = g_io_channel_unix_new(fd);
        ctx->io_source = g_io_add_watch(channel, condition, stmt_io_cb, ctx);
        g_io_channel_unref(channel);
    }
    if (ctx->wait_status & MYSQL_WAIT_TIMEOUT) {
        unsigned int timeout_ms = mysql_get_timeout_value_ms(ctx->con);
        if (timeout_ms == 0) timeout_ms = 1;
        ctx->timeout_source = g_timeout_add(timeout_ms, stmt_timeout_cb, ctx);
    }
    if (!ctx->io_source && !ctx->timeout_source)
        ctx->timeout_source = g_timeout_add(1, stmt_timeout_cb, ctx);
}

static void start_stmt_store(stmt_async_ctx_t *ctx) {
    my_bool update_max_length = 1;
    if (mysql_stmt_attr_set(ctx->stmt, STMT_ATTR_UPDATE_MAX_LENGTH,
                            &update_max_length) != 0) {
        finish_stmt_error(ctx, mysql_stmt_error(ctx->stmt));
        return;
    }
    ctx->phase = STMT_PHASE_STORE;
    ctx->result_code = 0;
    ctx->wait_status = mysql_stmt_store_result_start(&ctx->result_code,
                                                      ctx->stmt);
    if (ctx->wait_status) schedule_stmt_wait(ctx);
    else if (ctx->result_code != 0) finish_stmt_error(ctx, mysql_stmt_error(ctx->stmt));
    else finish_execute_success(ctx);
}

static void start_stmt_execute(stmt_async_ctx_t *ctx) {
    const char *err_msg = NULL;
    if (!bind_stmt_params(ctx, &err_msg)) {
        finish_stmt_error(ctx, err_msg);
        return;
    }
    ctx->phase = STMT_PHASE_EXECUTE;
    ctx->result_code = 0;
    ctx->wait_status = mysql_stmt_execute_start(&ctx->result_code, ctx->stmt);
    if (ctx->wait_status) schedule_stmt_wait(ctx);
    else if (ctx->result_code != 0) finish_stmt_error(ctx, mysql_stmt_error(ctx->stmt));
    else if (mysql_stmt_field_count(ctx->stmt) > 0) start_stmt_store(ctx);
    else finish_execute_success(ctx);
}

static void continue_stmt_operation(stmt_async_ctx_t *ctx, int event_status) {
    switch (ctx->phase) {
        case STMT_PHASE_PREPARE:
            ctx->wait_status = mysql_stmt_prepare_cont(&ctx->result_code,
                                                       ctx->stmt,
                                                       event_status);
            break;
        case STMT_PHASE_EXECUTE:
            ctx->wait_status = mysql_stmt_execute_cont(&ctx->result_code,
                                                       ctx->stmt,
                                                       event_status);
            break;
        case STMT_PHASE_STORE:
            ctx->wait_status = mysql_stmt_store_result_cont(&ctx->result_code,
                                                            ctx->stmt,
                                                            event_status);
            break;
    }
    if (ctx->wait_status) {
        schedule_stmt_wait(ctx);
        return;
    }
    if (ctx->result_code != 0) {
        finish_stmt_error(ctx, mysql_stmt_error(ctx->stmt));
        return;
    }
    if (ctx->phase == STMT_PHASE_PREPARE) {
        if (ctx->prepare_only) finish_prepare_success(ctx);
        else start_stmt_execute(ctx);
    } else if (ctx->phase == STMT_PHASE_EXECUTE &&
               mysql_stmt_field_count(ctx->stmt) > 0) {
        start_stmt_store(ctx);
    } else {
        finish_execute_success(ctx);
    }
}

static void start_stmt_prepare(stmt_async_ctx_t *ctx) {
    ctx->phase = STMT_PHASE_PREPARE;
    ctx->result_code = 0;
    ctx->wait_status = mysql_stmt_prepare_start(&ctx->result_code,
                                                ctx->stmt,
                                                ctx->sql,
                                                (unsigned long)ctx->sql_len);
    if (ctx->wait_status) schedule_stmt_wait(ctx);
    else if (ctx->result_code != 0) finish_stmt_error(ctx, mysql_stmt_error(ctx->stmt));
    else if (ctx->prepare_only) finish_prepare_success(ctx);
    else start_stmt_execute(ctx);
}

/* ---------------- 6. Funções Principais ---------------- */

static int l_mysql_exec_async(lua_State *L) {
    DBG("Entrando exec_async");

    ps_mysql_t *ud = check_pcon(L, 1);
    if (ud->closed) return push_nil_err(L, "conex\xC3\xA3o MySQL est\xC3\xA1 fechada");
    if (ud->busy) return push_nil_err(L, "conex\xC3\xA3o MariaDB ocupada");

    size_t len = 0;
    const char *query_lua = luaL_checklstring(L, 2, &len);
    luaL_checktype(L, 3, LUA_TFUNCTION);
    if (len > ULONG_MAX)
        return push_nil_err(L, "comando SQL grande demais");

    async_ctx_t *ctx = create_async_ctx(L, 3, 4);
    ctx->con = ud->con;
    ctx->connection = ud;
    ctx->query_len = len;
    ctx->query_str = g_memdup2(query_lua, len + 1);
    ud->busy = TRUE;

    ctx->phase = QUERY_PHASE_EXECUTE;
    ctx->wait_status = mysql_real_query_start(&ctx->result_code, ud->con, ctx->query_str, (unsigned long)len);

    DBG("query_start: wait=%d, res=%d", ctx->wait_status, ctx->result_code);

    if (ctx->wait_status == 0) {
        if (ctx->result_code != 0) {
            finish_query(ctx, mysql_error(ud->con));
        } else if (mysql_field_count(ud->con) != 0) {
            start_query_store(ctx);
        } else {
            finish_query(ctx, NULL);
        }
        return 0;
    }

    schedule_query_wait(ctx);
    return 0;
}

static stmt_async_ctx_t *prepare_stmt_context(lua_State *L,
                                               ps_mysql_t *connection,
                                               MYSQL_STMT *stmt,
                                               gboolean auto_close,
                                               int func_idx,
                                               int dado_idx) {
    stmt_async_ctx_t *ctx;
    ps_mysql_stmt_t *statement;
    ctx = new_stmt_ctx(L, func_idx, dado_idx);
    ctx->connection = connection;
    ctx->con = connection->con;

    lua_pushvalue(L, 1);
    ctx->con_ref = luaL_ref(L, LUA_REGISTRYINDEX);
    statement = push_new_pstmt(L, stmt, connection, 1, auto_close);
    ctx->statement = statement;
    ctx->stmt = stmt;
    ctx->stmt_ref = luaL_ref(L, LUA_REGISTRYINDEX);
    return ctx;
}

static int l_mysql_prepare_async(lua_State *L) {
    ps_mysql_t *connection = check_pcon(L, 1);
    size_t sql_len = 0;
    const char *sql;
    MYSQL_STMT *stmt;
    stmt_async_ctx_t *ctx;

    if (connection->closed)
        return push_nil_err(L, "conex\xC3\xA3o MariaDB fechada");
    if (connection->busy)
        return push_nil_err(L, "conex\xC3\xA3o MariaDB ocupada");
    sql = luaL_checklstring(L, 2, &sql_len);
    luaL_checktype(L, 3, LUA_TFUNCTION);
    if (sql_len > ULONG_MAX)
        return push_nil_err(L, "comando SQL grande demais");
    stmt = mysql_stmt_init(connection->con);
    if (!stmt) return push_nil_err(L, mysql_error(connection->con));

    ctx = prepare_stmt_context(L, connection, stmt, FALSE, 3, 4);
    ctx->prepare_only = TRUE;
    ctx->sql = g_memdup2(sql, sql_len + 1);
    ctx->sql_len = sql_len;
    connection->busy = TRUE;
    ctx->statement->busy = TRUE;
    start_stmt_prepare(ctx);
    return 0;
}

static int l_mysql_execute_prepared_async(lua_State *L) {
    ps_mysql_t *connection = check_pcon(L, 1);
    size_t sql_len = 0;
    const char *sql;
    MYSQL_STMT *stmt;
    stmt_async_ctx_t *ctx;

    if (connection->closed)
        return push_nil_err(L, "conex\xC3\xA3o MariaDB fechada");
    if (connection->busy)
        return push_nil_err(L, "conex\xC3\xA3o MariaDB ocupada");
    sql = luaL_checklstring(L, 2, &sql_len);
    luaL_checktype(L, 3, LUA_TTABLE);
    luaL_checktype(L, 4, LUA_TFUNCTION);
    if (sql_len > ULONG_MAX)
        return push_nil_err(L, "comando SQL grande demais");
    stmt = mysql_stmt_init(connection->con);
    if (!stmt) return push_nil_err(L, mysql_error(connection->con));

    ctx = prepare_stmt_context(L, connection, stmt, TRUE, 4, 5);
    ctx->prepare_only = FALSE;
    ctx->sql = g_memdup2(sql, sql_len + 1);
    ctx->sql_len = sql_len;
    lua_pushvalue(L, 3);
    ctx->params_ref = luaL_ref(L, LUA_REGISTRYINDEX);
    connection->busy = TRUE;
    ctx->statement->busy = TRUE;
    start_stmt_prepare(ctx);
    return 0;
}

static int l_stmt_execute_async(lua_State *L) {
    ps_mysql_stmt_t *statement = check_pstmt(L, 1);
    stmt_async_ctx_t *ctx;
    if (statement->closed)
        return push_nil_err(L, "consulta preparada fechada");
    if (!statement->connection || statement->connection->closed)
        return push_nil_err(L, "conex\xC3\xA3o MariaDB fechada");
    if (statement->busy)
        return push_nil_err(L, "a consulta preparada ainda est\xC3\xA1 em uso");
    if (statement->connection->busy)
        return push_nil_err(L, "conex\xC3\xA3o MariaDB ocupada");
    luaL_checktype(L, 2, LUA_TTABLE);
    luaL_checktype(L, 3, LUA_TFUNCTION);

    ctx = new_stmt_ctx(L, 3, 4);
    ctx->connection = statement->connection;
    ctx->statement = statement;
    ctx->con = statement->connection->con;
    ctx->stmt = statement->stmt;
    ctx->prepare_only = FALSE;
    ctx->con_ref = duplicate_registry_ref(L, statement->connection_ref);
    lua_pushvalue(L, 1);
    ctx->stmt_ref = luaL_ref(L, LUA_REGISTRYINDEX);
    lua_pushvalue(L, 2);
    ctx->params_ref = luaL_ref(L, LUA_REGISTRYINDEX);
    statement->connection->busy = TRUE;
    statement->busy = TRUE;
    start_stmt_execute(ctx);
    return 0;
}

static int l_stmt_param_count(lua_State *L) {
    ps_mysql_stmt_t *statement = check_pstmt(L, 1);
    if (statement->closed)
        return push_nil_err(L, "consulta preparada fechada");
    lua_pushinteger(L, (lua_Integer)mysql_stmt_param_count(statement->stmt));
    return 1;
}

static int l_mysql_conecte_async(lua_State *L) {
    DBG("conecteAss\xC3\xADncrono iniciado");

    const char *host_lua = luaL_checkstring(L, 1);
    const char *user_lua = luaL_checkstring(L, 2);
    const char *pass_lua = luaL_checkstring(L, 3);
    const char *db_lua   = luaL_checkstring(L, 4);
    lua_Integer port_lua = luaL_optinteger(L, 5, 3306);
    unsigned int port;
    luaL_checktype(L, 6, LUA_TFUNCTION);
    if (port_lua < 1 || port_lua > 65535)
        return push_nil_err(L, "a porta deve estar entre 1 e 65535");
    port = (unsigned int)port_lua;

    MYSQL *con = mysql_init(NULL);
    if (!con) return push_nil_err(L, "mysql_init falhou");

    /* NONBLOCK é obrigatório antes de qualquer chamada *_start. */
    if (mysql_options(con, MYSQL_OPT_NONBLOCK, 0) != 0 ||
        mysql_options(con, MYSQL_SET_CHARSET_NAME, "utf8mb4") != 0) {
        char *message = g_strdup(mysql_error(con));
        mysql_close(con);
        int result = push_nil_err(L, message && message[0]
                                      ? message
                                      : "falha ao configurar a conex\xC3\xA3o MariaDB");
        g_free(message);
        return result;
    }

    connect_ctx_t *ctx = create_connect_ctx(L, 6, 7);
    ctx->con = con;
    ctx->ret_con = NULL;

    // Copia strings para garantir persistência
    ctx->host = g_strdup(host_lua);
    ctx->user = g_strdup(user_lua);
    ctx->pass = g_strdup(pass_lua);
    ctx->db   = g_strdup(db_lua);

    ctx->wait_status = mysql_real_connect_start(&ctx->ret_con, con,
                        ctx->host, ctx->user, ctx->pass, ctx->db,
                        port, NULL, 0);

    DBG("connect_start: wait=%d", ctx->wait_status);

    if (ctx->wait_status == 0) {
        finish_connect(ctx);
        return 0;
    }

    schedule_connect_wait(ctx);
    return 0;
}

// Funções auxiliares (escape, info, resultado...)
static int l_mysql_escape_string(lua_State *L) {
    ps_mysql_t *ud = check_pcon(L, 1);
    if (ud->closed) return push_nil_err(L, "fechada");
    if (ud->busy) return push_nil_err(L, "conex\xC3\xA3o MariaDB ocupada");
    size_t len=0; const char *s = luaL_checklstring(L,2,&len);
    if (len > ULONG_MAX || len > (G_MAXSIZE - 1) / 2)
        return push_nil_err(L, "colar grande demais para escapar");
    char *buf = g_malloc(len*2+1);
    unsigned long escaped = mysql_real_escape_string(ud->con, buf, s,
                                                       (unsigned long)len);
    lua_pushlstring(L, buf, escaped);
    g_free(buf);
    return 1;
}

static int l_mysql_info(lua_State *L) { lua_pushstring(L, mysql_get_client_info()); return 1; }

static int l_res_fetch_row(lua_State *L) {
    ps_mysql_res_t *ud = check_pres(L, 1);
    if (ud->closed) return push_nil_err(L, "fechado");
    if (ud->kind == PS_RESULT_STMT) {
        int status = mysql_stmt_fetch(ud->stmt);
        if (status == MYSQL_NO_DATA) {
            lua_pushnil(L);
            return 1;
        }
        if (status != 0 && status != MYSQL_DATA_TRUNCATED)
            return push_nil_err(L, mysql_stmt_error(ud->stmt));

        gboolean rebound = FALSE;
        if (status == MYSQL_DATA_TRUNCATED) {
            for (int i = 0; i < ud->num_fields; i++) {
                ps_stmt_column_t *column = &ud->columns[i];
                if (!column->error || column->is_null) continue;
                if ((guint64)column->length > (guint64)G_MAXSIZE - 1)
                    return push_nil_err(L, "coluna grande demais");
                column->buffer = g_realloc(column->buffer,
                                            (gsize)column->length + 1);
                column->bind.buffer = column->buffer;
                column->bind.buffer_length = column->length + 1;
                ud->stmt_binds[i] = column->bind;
                if (mysql_stmt_fetch_column(ud->stmt, &ud->stmt_binds[i],
                                            (unsigned int)i, 0) != 0)
                    return push_nil_err(L, mysql_stmt_error(ud->stmt));
                rebound = TRUE;
            }
        }

        lua_createtable(L, ud->num_fields, 0);
        for (int i = 0; i < ud->num_fields; i++) {
            ps_stmt_column_t *column = &ud->columns[i];
            if (column->is_null) lua_pushnil(L);
            else lua_pushlstring(L, column->buffer, column->length);
            lua_rawseti(L, -2, i + 1);
            column->error = 0;
        }
        if (rebound && mysql_stmt_bind_result(ud->stmt, ud->stmt_binds) != 0) {
            lua_pop(L, 1);
            return push_nil_err(L, mysql_stmt_error(ud->stmt));
        }
        return 1;
    }

    if (!ud->res) {
        lua_pushnil(L);
        return 1;
    }
    MYSQL_ROW row = mysql_fetch_row(ud->res);
    if (row) {
        unsigned long *len = mysql_fetch_lengths(ud->res);
        lua_createtable(L, ud->num_fields, 0);
        for(int i=0; i<ud->num_fields; i++) {
            if (row[i]) lua_pushlstring(L, row[i], len[i]);
            else lua_pushnil(L);
            lua_rawseti(L, -2, i+1);
        }
        return 1;
    }
    if (ud->connection && !ud->connection->closed &&
        mysql_errno(ud->connection->con) != 0)
        return push_nil_err(L, mysql_error(ud->connection->con));
    lua_pushnil(L); return 1;
}
static int l_res_num_rows(lua_State *L) {
    ps_mysql_res_t *ud = check_pres(L, 1);
    if (ud->closed) return push_nil_err(L, "fechado");
    if (ud->kind == PS_RESULT_STMT)
        push_mysql_uint(L, mysql_stmt_num_rows(ud->stmt));
    else
        push_mysql_uint(L, ud->res ? mysql_num_rows(ud->res) : 0);
    return 1;
}

static int l_res_affected_rows(lua_State *L) {
    ps_mysql_res_t *ud = check_pres(L, 1);
    if (ud->closed) return push_nil_err(L, "fechado");
    push_mysql_uint(L, ud->affected_rows);
    return 1;
}

static int l_res_insert_id(lua_State *L) {
    ps_mysql_res_t *ud = check_pres(L, 1);
    if (ud->closed) return push_nil_err(L, "fechado");
    push_mysql_uint(L, ud->insert_id);
    return 1;
}

/* ---------------- 7. Piscina, sessões e transações ---------------- */

static ps_mysql_pool_t *check_pool(lua_State *L, int idx) {
    return (ps_mysql_pool_t*)luaL_checkudata(L, idx, PS_MYSQL_POOL);
}

static ps_mysql_session_t *check_session(lua_State *L, int idx) {
    return (ps_mysql_session_t*)luaL_checkudata(L, idx, PS_MYSQL_SESSION);
}

static ps_mysql_session_t *check_transaction(lua_State *L, int idx) {
    return (ps_mysql_session_t*)luaL_checkudata(L, idx,
                                                PS_MYSQL_TRANSACTION);
}

static int duplicate_ref(lua_State *L, int ref) {
    if (ref == LUA_NOREF || ref == LUA_REFNIL) return LUA_NOREF;
    lua_rawgeti(L, LUA_REGISTRYINDEX, ref);
    return luaL_ref(L, LUA_REGISTRYINDEX);
}

static gboolean pool_entry_clean(pool_entry_t *entry) {
    ps_mysql_t *connection = entry ? entry->connection : NULL;
    return connection && !connection->busy &&
           connection->open_statements == 0 &&
           connection->open_results == 0;
}

static void pool_close_entry(lua_State *L, pool_entry_t *entry) {
    ps_mysql_t *connection;
    if (!entry) return;
    connection = entry->connection;
    if (connection && !connection->closed && pool_entry_clean(entry)) {
        mysql_close(connection->con);
        connection->con = NULL;
        connection->closed = TRUE;
    }
    if (entry->connection_ref != LUA_NOREF) {
        luaL_unref(L, LUA_REGISTRYINDEX, entry->connection_ref);
        entry->connection_ref = LUA_NOREF;
    }
    entry->connection = NULL;
    entry->state = POOL_ENTRY_EMPTY;
    entry->generation++;
}

static int pool_active_count(ps_mysql_pool_t *pool) {
    int count = 0;
    for (int i = 0; i < pool->maximum; i++)
        if (pool->entries[i].state != POOL_ENTRY_EMPTY)
            count++;
    return count;
}

static int pool_state_count(ps_mysql_pool_t *pool, pool_entry_state_t state) {
    int count = 0;
    for (int i = 0; i < pool->maximum; i++)
        if (pool->entries[i].state == state) count++;
    return count;
}

static pool_entry_t *pool_find_entry(ps_mysql_pool_t *pool,
                                     pool_entry_state_t state) {
    for (int i = 0; i < pool->maximum; i++)
        if (pool->entries[i].state == state) return &pool->entries[i];
    return NULL;
}

static gboolean pool_connection_broken(pool_entry_t *entry) {
    unsigned int error;
    if (!entry || !entry->connection || entry->connection->closed)
        return TRUE;
    error = mysql_errno(entry->connection->con);
#ifdef CR_SERVER_GONE_ERROR
    if (error == CR_SERVER_GONE_ERROR) return TRUE;
#endif
#ifdef CR_SERVER_LOST
    if (error == CR_SERVER_LOST) return TRUE;
#endif
    return error == 2006 || error == 2013;
}

static void pool_free_job(pool_job_t *job) {
    if (!job) return;
    if (job->timeout_source) {
        g_source_remove(job->timeout_source);
        job->timeout_source = 0;
    }
    if (job->callback_ref != LUA_NOREF)
        luaL_unref(job->pool->L, LUA_REGISTRYINDEX, job->callback_ref);
    if (job->pool_ref != LUA_NOREF)
        luaL_unref(job->pool->L, LUA_REGISTRYINDEX, job->pool_ref);
    if (job->params_ref != LUA_NOREF)
        luaL_unref(job->pool->L, LUA_REGISTRYINDEX, job->params_ref);
    g_free(job->sql);
    g_free(job);
}

static void pool_invoke_job_error(pool_job_t *job, const char *message) {
    lua_State *L = job->pool->L;
    push_stored_callback(L, job->callback_ref, "func");
    lua_rawgeti(L, LUA_REGISTRYINDEX, job->pool_ref);
    lua_pushnil(L);
    lua_pushstring(L, message ? message : "falha na piscina MariaDB");
    push_stored_callback(L, job->callback_ref, "dado");
    if (lua_pcall(L, 4, 0, 0) != 0) {
        g_printerr("piscina MariaDB retornou erro: %s\n",
                   lua_tostring(L, -1));
        lua_pop(L, 1);
    }
}

static void pool_fail_job(pool_job_t *job, const char *message) {
    pool_invoke_job_error(job, message);
    pool_free_job(job);
}

static ps_mysql_session_t *push_new_session(lua_State *L,
                                             ps_mysql_pool_t *pool,
                                             pool_entry_t *entry,
                                             int pool_ref,
                                             gboolean transaction) {
    const char *metatable = transaction ? PS_MYSQL_TRANSACTION
                                        : PS_MYSQL_SESSION;
    ps_mysql_session_t *session =
        (ps_mysql_session_t*)lua_newuserdata(L, sizeof(*session));
    memset(session, 0, sizeof(*session));
    session->pool = pool;
    session->entry = entry;
    session->pool_ref = duplicate_ref(L, pool_ref);
    session->active = TRUE;
    session->transaction = transaction;
    session->generation = ++entry->generation;
    entry->state = transaction ? POOL_ENTRY_TRANSACTION
                               : POOL_ENTRY_SESSION;
    luaL_getmetatable(L, metatable);
    lua_setmetatable(L, -2);
    return session;
}

static gboolean session_is_valid(ps_mysql_session_t *session) {
    return session && session->active && session->pool && session->entry &&
           !session->pool->closed &&
           session->entry->generation == session->generation &&
           session->entry->connection &&
           !session->entry->connection->closed;
}

static void pool_dispatch(ps_mysql_pool_t *pool, int pool_ref);
static void pool_start_connection(ps_mysql_pool_t *pool, int pool_ref,
                                  gboolean initial);
static void pool_start_job(pool_job_t *job, pool_entry_t *entry);

static gboolean pool_job_timeout_cb(gpointer user_data) {
    pool_job_t *job = (pool_job_t*)user_data;
    ps_mysql_pool_t *pool = job->pool;
    job->timeout_source = 0;
    if (!job->queued) return G_SOURCE_REMOVE;
    if (g_queue_remove(pool->queue, job)) {
        job->queued = FALSE;
        pool_fail_job(job,
                      "tempo de espera esgotado na fila da piscina MariaDB");
    }
    return G_SOURCE_REMOVE;
}

static void pool_queue_job(pool_job_t *job) {
    ps_mysql_pool_t *pool = job->pool;
    job->queued = TRUE;
    g_queue_push_tail(pool->queue, job);
    if (pool->wait_ms > 0)
        job->timeout_source = g_timeout_add(pool->wait_ms,
                                            pool_job_timeout_cb, job);
    pool_dispatch(pool, job->pool_ref);
}

static pool_job_t *new_pool_job(lua_State *L, ps_mysql_pool_t *pool,
                                pool_job_kind_t kind, int callback_idx,
                                int data_idx, int pool_idx) {
    pool_job_t *job = g_new0(pool_job_t, 1);
    job->pool = pool;
    job->kind = kind;
    job->callback_ref = store_callback(L, callback_idx, data_idx);
    lua_pushvalue(L, pool_idx);
    job->pool_ref = luaL_ref(L, LUA_REGISTRYINDEX);
    job->params_ref = LUA_NOREF;
    return job;
}

static void pool_dispatch(ps_mysql_pool_t *pool, int pool_ref) {
    pool_entry_t *entry;
    while (!pool->closed && !g_queue_is_empty(pool->queue) &&
           (entry = pool_find_entry(pool, POOL_ENTRY_FREE)) != NULL) {
        pool_job_t *job = (pool_job_t*)g_queue_pop_head(pool->queue);
        job->queued = FALSE;
        if (job->timeout_source) {
            g_source_remove(job->timeout_source);
            job->timeout_source = 0;
        }
        pool_start_job(job, entry);
    }
    while (!pool->closed && !g_queue_is_empty(pool->queue) &&
           pool_active_count(pool) < pool->maximum &&
           pool_state_count(pool, POOL_ENTRY_CONNECTING) <
               (int)g_queue_get_length(pool->queue)) {
        pool_start_connection(pool, pool_ref, FALSE);
    }
}

static void pool_invoke_initial(ps_mysql_pool_t *pool, int pool_ref) {
    lua_State *L = pool->L;
    if (pool->initial_callback_ref == LUA_NOREF) return;
    push_stored_callback(L, pool->initial_callback_ref, "func");
    if (pool->initial_error) {
        lua_pushnil(L);
        lua_pushstring(L, pool->initial_error);
    } else {
        lua_rawgeti(L, LUA_REGISTRYINDEX, pool_ref);
        lua_pushnil(L);
    }
    push_stored_callback(L, pool->initial_callback_ref, "dado");
    if (lua_pcall(L, 3, 0, 0) != 0) {
        g_printerr("criePiscinaAss\xC3\xADncrona retornou erro: %s\n",
                   lua_tostring(L, -1));
        lua_pop(L, 1);
    }
    luaL_unref(L, LUA_REGISTRYINDEX, pool->initial_callback_ref);
    pool->initial_callback_ref = LUA_NOREF;
}

static void pool_finish_connect_attempt(pool_connect_attempt_t *attempt,
                                        int connection_idx,
                                        const char *error_message) {
    ps_mysql_pool_t *pool = attempt->pool;
    pool_entry_t *entry = attempt->entry;
    lua_State *L = attempt->L;

    if (!error_message && connection_idx != 0) {
        ps_mysql_t *connection = check_pcon(L, connection_idx);
        lua_pushvalue(L, connection_idx);
        entry->connection_ref = luaL_ref(L, LUA_REGISTRYINDEX);
        entry->connection = connection;
        entry->state = POOL_ENTRY_FREE;
    } else {
        entry->state = POOL_ENTRY_EMPTY;
        if (attempt->initial && !pool->initial_error)
            pool->initial_error = g_strdup(error_message ? error_message
                                              : "falha ao conectar a piscina MariaDB");
    }

    if (attempt->initial) {
        pool->initial_pending--;
        if (pool->initial_pending == 0) {
            pool->initializing = FALSE;
            if (pool->initial_error) {
                pool->closed = TRUE;
                for (int i = 0; i < pool->maximum; i++)
                    if (pool->entries[i].state == POOL_ENTRY_FREE)
                        pool_close_entry(L, &pool->entries[i]);
            } else {
                pool->ready = TRUE;
            }
            pool_invoke_initial(pool, attempt->pool_ref);
        }
    } else if (error_message) {
        pool_job_t *job = (pool_job_t*)g_queue_pop_head(pool->queue);
        if (job) {
            job->queued = FALSE;
            if (job->timeout_source) {
                g_source_remove(job->timeout_source);
                job->timeout_source = 0;
            }
            pool_fail_job(job, error_message);
        }
    }

    if (!attempt->initial && !pool->closed)
        pool_dispatch(pool, attempt->pool_ref);
    attempt->completed = TRUE;
}

static int pool_connect_adapter(lua_State *L) {
    pool_connect_attempt_t *attempt =
        (pool_connect_attempt_t*)lua_touserdata(L, lua_upvalueindex(1));
    const char *error_message = lua_tostring(L, 2);
    int connection_idx = luaL_testudata(L, 1, PS_MYSQL_CON) ? 1 : 0;
    pool_finish_connect_attempt(attempt, connection_idx, error_message);
    if (!attempt->dispatching) {
        luaL_unref(L, LUA_REGISTRYINDEX, attempt->pool_ref);
        g_free(attempt);
    }
    return 0;
}

static void pool_start_connection(ps_mysql_pool_t *pool, int pool_ref,
                                  gboolean initial) {
    lua_State *L = pool->L;
    pool_entry_t *entry = pool_find_entry(pool, POOL_ENTRY_EMPTY);
    pool_connect_attempt_t *attempt;
    int base;
    char *error_copy = NULL;
    if (!entry || pool->closed) return;
    entry->state = POOL_ENTRY_CONNECTING;
    entry->connection_ref = LUA_NOREF;
    attempt = g_new0(pool_connect_attempt_t, 1);
    attempt->L = L;
    attempt->pool = pool;
    attempt->entry = entry;
    attempt->pool_ref = duplicate_ref(L, pool_ref);
    attempt->initial = initial;
    attempt->dispatching = TRUE;

    base = lua_gettop(L);
    lua_pushcfunction(L, l_mysql_conecte_async);
    lua_pushstring(L, pool->host);
    lua_pushstring(L, pool->user);
    lua_pushstring(L, pool->password);
    lua_pushstring(L, pool->database);
    lua_pushinteger(L, pool->port);
    lua_pushlightuserdata(L, attempt);
    lua_pushcclosure(L, pool_connect_adapter, 1);
    lua_pushnil(L);
    if (lua_pcall(L, 7, 2, 0) != 0) {
        error_copy = g_strdup(lua_tostring(L, -1));
    } else if (lua_isstring(L, -1)) {
        error_copy = g_strdup(lua_tostring(L, -1));
    }
    lua_settop(L, base);
    attempt->dispatching = FALSE;
    if (error_copy && !attempt->completed)
        pool_finish_connect_attempt(attempt, 0, error_copy);
    g_free(error_copy);
    if (attempt->completed) {
        luaL_unref(L, LUA_REGISTRYINDEX, attempt->pool_ref);
        g_free(attempt);
    }
}

static const char *pool_get_string(lua_State *L, int table_idx,
                                   const char *field, gboolean required,
                                   char **target) {
    const char *value;
    table_idx = lua_absindex(L, table_idx);
    lua_getfield(L, table_idx, field);
    if (lua_isnil(L, -1)) {
        lua_pop(L, 1);
        if (required) return field;
        *target = g_strdup("");
        return NULL;
    }
    if (!lua_isstring(L, -1)) {
        lua_pop(L, 1);
        return field;
    }
    value = lua_tostring(L, -1);
    *target = g_strdup(value);
    lua_pop(L, 1);
    return NULL;
}

static lua_Integer pool_get_integer(lua_State *L, int table_idx,
                                    const char *field,
                                    lua_Integer default_value) {
    lua_Integer value;
    table_idx = lua_absindex(L, table_idx);
    lua_getfield(L, table_idx, field);
    value = lua_isnil(L, -1) ? default_value : luaL_checkinteger(L, -1);
    lua_pop(L, 1);
    return value;
}

static int l_mysql_create_pool_async(lua_State *L) {
    ps_mysql_pool_t *pool;
    const char *bad_field = NULL;
    lua_Integer minimum, maximum, max_queue, wait_ms, port;
    int pool_ref;
    luaL_checktype(L, 1, LUA_TTABLE);
    luaL_checktype(L, 2, LUA_TFUNCTION);

    pool = (ps_mysql_pool_t*)lua_newuserdata(L, sizeof(*pool));
    memset(pool, 0, sizeof(*pool));
    pool->L = L;
    pool->initial_callback_ref = LUA_NOREF;
    pool->queue = g_queue_new();
    bad_field = pool_get_string(L, 1, "endere\xC3\xA7o", TRUE,
                                &pool->host);
    if (!bad_field)
        bad_field = pool_get_string(L, 1, "usu\xC3\xA1rio", TRUE,
                                    &pool->user);
    if (!bad_field)
        bad_field = pool_get_string(L, 1, "senha", FALSE,
                                    &pool->password);
    if (!bad_field)
        bad_field = pool_get_string(L, 1, "banco", TRUE,
                                    &pool->database);
    if (bad_field) {
        g_free(pool->host); g_free(pool->user); g_free(pool->password);
        g_free(pool->database); g_queue_free(pool->queue);
        lua_pop(L, 1);
        return luaL_error(L, "campo '%s' ausente ou inv\xC3\xA1lido", bad_field);
    }

    minimum = pool_get_integer(L, 1, "m\xC3\xADnimo", 2);
    maximum = pool_get_integer(L, 1, "m\xC3\xA1ximo", 10);
    max_queue = pool_get_integer(L, 1, "m\xC3\xA1ximoDaFila", 100);
    wait_ms = pool_get_integer(L, 1, "tempoDeEspera", 5000);
    port = pool_get_integer(L, 1, "porta", 3306);
    if (minimum < 1 || maximum < minimum || maximum > 1024 ||
        max_queue < 0 || max_queue > 100000 || wait_ms < 0 ||
        wait_ms > G_MAXUINT || port < 1 || port > 65535) {
        g_free(pool->host); g_free(pool->user); g_free(pool->password);
        g_free(pool->database); g_queue_free(pool->queue);
        lua_pop(L, 1);
        return push_nil_err(L, "configura\xC3\xA7\xC3\xA3o inv\xC3\xA1lida da piscina MariaDB");
    }
    pool->minimum = (int)minimum;
    pool->maximum = (int)maximum;
    pool->max_queue = (int)max_queue;
    pool->wait_ms = (guint)wait_ms;
    pool->port = (unsigned int)port;
    pool->entries = g_new0(pool_entry_t, pool->maximum);
    for (int i = 0; i < pool->maximum; i++) {
        pool->entries[i].pool = pool;
        pool->entries[i].state = POOL_ENTRY_EMPTY;
        pool->entries[i].connection_ref = LUA_NOREF;
    }
    pool->initial_callback_ref = store_callback(L, 2, 3);
    pool->initializing = TRUE;
    pool->initial_pending = pool->minimum;
    luaL_getmetatable(L, PS_MYSQL_POOL);
    lua_setmetatable(L, -2);
    pool_ref = luaL_ref(L, LUA_REGISTRYINDEX);
    for (int i = 0; i < pool->minimum; i++)
        pool_start_connection(pool, pool_ref, TRUE);
    luaL_unref(L, LUA_REGISTRYINDEX, pool_ref);
    return 0;
}

static int l_pool_acquire_async(lua_State *L) {
    ps_mysql_pool_t *pool = check_pool(L, 1);
    pool_job_t *job;
    luaL_checktype(L, 2, LUA_TFUNCTION);
    if (pool->closed) return push_nil_err(L, "piscina MariaDB fechada");
    if (!pool->ready) return push_nil_err(L, "piscina MariaDB ainda n\xC3\xA3o est\xC3\xA1 pronta");
    if (!pool_find_entry(pool, POOL_ENTRY_FREE) &&
        pool_active_count(pool) >= pool->maximum &&
        (int)g_queue_get_length(pool->queue) >= pool->max_queue)
        return push_nil_err(L, "fila da piscina MariaDB cheia");
    job = new_pool_job(L, pool, POOL_JOB_ACQUIRE, 2, 3, 1);
    pool_queue_job(job);
    return 0;
}

static int l_pool_state(lua_State *L) {
    ps_mysql_pool_t *pool = check_pool(L, 1);
    lua_createtable(L, 0, 10);
#define POOL_STATE_FIELD(name, value) \
    do { lua_pushinteger(L, (lua_Integer)(value)); lua_setfield(L, -2, (name)); } while (0)
    POOL_STATE_FIELD("m\xC3\xADnimo", pool->minimum);
    POOL_STATE_FIELD("m\xC3\xA1ximo", pool->maximum);
    POOL_STATE_FIELD("total", pool_active_count(pool));
    POOL_STATE_FIELD("livres", pool_state_count(pool, POOL_ENTRY_FREE));
    POOL_STATE_FIELD("conectando", pool_state_count(pool, POOL_ENTRY_CONNECTING));
    POOL_STATE_FIELD("emOpera\xC3\xA7\xC3\xA3o", pool_state_count(pool, POOL_ENTRY_OPERATION));
    POOL_STATE_FIELD("sess\xC3\xB5" "es", pool_state_count(pool, POOL_ENTRY_SESSION));
    POOL_STATE_FIELD("transa\xC3\xA7\xC3\xB5" "es", pool_state_count(pool, POOL_ENTRY_TRANSACTION));
    POOL_STATE_FIELD("naFila", g_queue_get_length(pool->queue));
#undef POOL_STATE_FIELD
    lua_pushboolean(L, pool->closed); lua_setfield(L, -2, "fechada");
    return 1;
}

static int l_pool_close(lua_State *L) {
    ps_mysql_pool_t *pool = check_pool(L, 1);
    if (pool->closed) return 0;
    if (pool_state_count(pool, POOL_ENTRY_CONNECTING) > 0 ||
        pool_state_count(pool, POOL_ENTRY_OPERATION) > 0 ||
        pool_state_count(pool, POOL_ENTRY_SESSION) > 0 ||
        pool_state_count(pool, POOL_ENTRY_TRANSACTION) > 0 ||
        !g_queue_is_empty(pool->queue))
        return push_nil_err(L, "a piscina MariaDB ainda possui opera\xC3\xA7\xC3\xB5" "es, sess\xC3\xB5" "es ou transa\xC3\xA7\xC3\xB5" "es ativas");
    for (int i = 0; i < pool->maximum; i++) {
        if (pool->entries[i].state == POOL_ENTRY_FREE &&
            !pool_entry_clean(&pool->entries[i]))
            return push_nil_err(L, "feche resultados e consultas antes da piscina");
    }
    pool->closed = TRUE;
    for (int i = 0; i < pool->maximum; i++)
        if (pool->entries[i].state == POOL_ENTRY_FREE ||
            pool->entries[i].state == POOL_ENTRY_DEAD)
            pool_close_entry(L, &pool->entries[i]);
    return 0;
}

static int l_pool_gc(lua_State *L) {
    ps_mysql_pool_t *pool = check_pool(L, 1);
    if (!pool->closed && g_queue_is_empty(pool->queue) &&
        pool_state_count(pool, POOL_ENTRY_CONNECTING) == 0 &&
        pool_state_count(pool, POOL_ENTRY_OPERATION) == 0 &&
        pool_state_count(pool, POOL_ENTRY_SESSION) == 0 &&
        pool_state_count(pool, POOL_ENTRY_TRANSACTION) == 0) {
        for (int i = 0; i < pool->maximum; i++)
            if (pool->entries[i].state == POOL_ENTRY_FREE &&
                pool_entry_clean(&pool->entries[i]))
                pool_close_entry(L, &pool->entries[i]);
        pool->closed = TRUE;
    }
    if (pool->closed && pool->entries) {
        g_free(pool->entries); pool->entries = NULL;
        if (pool->queue) { g_queue_free(pool->queue); pool->queue = NULL; }
        g_free(pool->host); pool->host = NULL;
        g_free(pool->user); pool->user = NULL;
        g_free(pool->password); pool->password = NULL;
        g_free(pool->database); pool->database = NULL;
        g_free(pool->initial_error); pool->initial_error = NULL;
    }
    return 0;
}

static void pool_close_result_at(lua_State *L, int index) {
    int base = lua_gettop(L);
    index = lua_absindex(L, index);
    if (!luaL_testudata(L, index, PS_MYSQL_RES)) return;
    lua_pushcfunction(L, l_res_close);
    lua_pushvalue(L, index);
    if (lua_pcall(L, 1, 0, 0) != 0) lua_pop(L, 1);
    lua_settop(L, base);
}

static void pool_attach_scope(lua_State *L, int value_idx,
                              int scope_ref) {
    ps_mysql_res_t *result;
    ps_mysql_stmt_t *statement;
    value_idx = lua_absindex(L, value_idx);
    result = (ps_mysql_res_t*)luaL_testudata(L, value_idx, PS_MYSQL_RES);
    if (result) {
        if (result->kind == PS_RESULT_QUERY) {
            if (result->scope_ref == LUA_NOREF)
                result->scope_ref = duplicate_ref(L, scope_ref);
        } else if (result->owner && result->owner->lease_ref == LUA_NOREF) {
            result->owner->lease_ref = duplicate_ref(L, scope_ref);
        }
        return;
    }
    statement = (ps_mysql_stmt_t*)luaL_testudata(L, value_idx,
                                                  PS_MYSQL_STMT);
    if (statement && statement->lease_ref == LUA_NOREF)
        statement->lease_ref = duplicate_ref(L, scope_ref);
}

static void pool_release_entry(ps_mysql_pool_t *pool, pool_entry_t *entry,
                               int pool_ref, gboolean discard) {
    if (!entry) return;
    if (discard || pool_connection_broken(entry)) {
        entry->state = POOL_ENTRY_DEAD;
        if (pool_entry_clean(entry)) pool_close_entry(pool->L, entry);
    } else {
        entry->state = POOL_ENTRY_FREE;
    }
    if (!pool->closed) {
        pool_dispatch(pool, pool_ref);
        while (pool_active_count(pool) < pool->minimum)
            pool_start_connection(pool, pool_ref, FALSE);
    }
}

static void pool_result_release_hook(lua_State *L, void *data) {
    pool_result_lease_t *lease = (pool_result_lease_t*)data;
    if (!lease) return;
    pool_release_entry(lease->pool, lease->entry, lease->pool_ref, FALSE);
    if (lease->pool_ref != LUA_NOREF)
        luaL_unref(L, LUA_REGISTRYINDEX, lease->pool_ref);
    g_free(lease);
}

static gboolean pool_attach_result_lease(lua_State *L, int value_idx,
                                         pool_op_t *op) {
    ps_mysql_res_t *result = (ps_mysql_res_t*)luaL_testudata(
                                L, value_idx, PS_MYSQL_RES);
    pool_result_lease_t *lease;
    if (!result || result->close_hook) return FALSE;
    lease = g_new0(pool_result_lease_t, 1);
    lease->pool = op->pool;
    lease->entry = op->entry;
    lease->pool_ref = duplicate_ref(L, op->scope_ref);
    result->close_hook = pool_result_release_hook;
    result->close_hook_data = lease;
    return TRUE;
}

static void pool_free_op(pool_op_t *op) {
    if (!op) return;
    if (op->callback_ref != LUA_NOREF)
        luaL_unref(op->L, LUA_REGISTRYINDEX, op->callback_ref);
    if (op->scope_ref != LUA_NOREF)
        luaL_unref(op->L, LUA_REGISTRYINDEX, op->scope_ref);
    if (op->params_ref != LUA_NOREF)
        luaL_unref(op->L, LUA_REGISTRYINDEX, op->params_ref);
    g_free(op->sql);
    g_free(op);
}

static void pool_invoke_operation_callback(pool_op_t *op, int value_idx,
                                           const char *error_message) {
    lua_State *L = op->L;
    push_stored_callback(L, op->callback_ref, "func");
    lua_rawgeti(L, LUA_REGISTRYINDEX, op->scope_ref);
    if (value_idx != 0 && !error_message)
        lua_pushvalue(L, lua_absindex(L, value_idx));
    else
        lua_pushnil(L);
    if (error_message) lua_pushstring(L, error_message);
    else lua_pushnil(L);
    push_stored_callback(L, op->callback_ref, "dado");
    if (lua_pcall(L, 4, 0, 0) != 0) {
        g_printerr("opera\xC3\xA7\xC3\xA3o da piscina MariaDB retornou erro: %s\n",
                   lua_tostring(L, -1));
        lua_pop(L, 1);
    }
}

static void pool_finish_operation(pool_op_t *op, int value_idx,
                                  const char *error_message) {
    lua_State *L = op->L;
    gboolean broken = error_message && pool_connection_broken(op->entry);
    int absolute_value = value_idx ? lua_absindex(L, value_idx) : 0;

    if (!error_message && absolute_value)
        pool_attach_scope(L, absolute_value, op->scope_ref);

    if (op->kind == POOL_OP_BEGIN) {
        if (absolute_value) pool_close_result_at(L, absolute_value);
        if (error_message) {
            pool_release_entry(op->pool, op->entry, op->scope_ref, broken);
            pool_invoke_operation_callback(op, 0, error_message);
        } else {
            push_stored_callback(L, op->callback_ref, "func");
            lua_rawgeti(L, LUA_REGISTRYINDEX, op->scope_ref);
            push_new_session(L, op->pool, op->entry, op->scope_ref, TRUE);
            lua_pushnil(L);
            push_stored_callback(L, op->callback_ref, "dado");
            if (lua_pcall(L, 4, 0, 0) != 0) {
                g_printerr("inicieTransa\xC3\xA7\xC3\xA3oAss\xC3\xADncrona retornou erro: %s\n",
                           lua_tostring(L, -1));
                lua_pop(L, 1);
            }
        }
    } else if (op->kind == POOL_OP_COMMIT ||
               op->kind == POOL_OP_ROLLBACK) {
        ps_mysql_session_t *transaction;
        if (absolute_value) pool_close_result_at(L, absolute_value);
        lua_rawgeti(L, LUA_REGISTRYINDEX, op->scope_ref);
        transaction = (ps_mysql_session_t*)luaL_testudata(
                            L, -1, PS_MYSQL_TRANSACTION);
        lua_pop(L, 1);
        if (!error_message || op->kind == POOL_OP_ROLLBACK || broken) {
            if (transaction) transaction->active = FALSE;
            pool_release_entry(op->pool, op->entry,
                               transaction && transaction->pool_ref != LUA_NOREF
                                   ? transaction->pool_ref : op->scope_ref,
                               error_message != NULL);
        }
        push_stored_callback(L, op->callback_ref, "func");
        lua_rawgeti(L, LUA_REGISTRYINDEX, op->scope_ref);
        if (error_message) lua_pushnil(L); else lua_pushboolean(L, 1);
        if (error_message) lua_pushstring(L, error_message); else lua_pushnil(L);
        push_stored_callback(L, op->callback_ref, "dado");
        if (lua_pcall(L, 4, 0, 0) != 0) {
            g_printerr("finaliza\xC3\xA7\xC3\xA3o da transa\xC3\xA7\xC3\xA3o retornou erro: %s\n",
                       lua_tostring(L, -1));
            lua_pop(L, 1);
        }
        if (transaction && !transaction->active) {
            if (transaction->pool_ref != LUA_NOREF)
                luaL_unref(L, LUA_REGISTRYINDEX, transaction->pool_ref);
            transaction->pool_ref = LUA_NOREF;
            transaction->entry = NULL;
            transaction->pool = NULL;
        }
    } else {
        if (op->release_after) {
            if (error_message || !absolute_value ||
                !pool_attach_result_lease(L, absolute_value, op))
                pool_release_entry(op->pool, op->entry, op->scope_ref,
                                   broken);
        }
        else if (broken) {
            lua_rawgeti(L, LUA_REGISTRYINDEX, op->scope_ref);
            ps_mysql_session_t *session =
                (ps_mysql_session_t*)luaL_testudata(L, -1,
                    op->entry->state == POOL_ENTRY_TRANSACTION
                        ? PS_MYSQL_TRANSACTION : PS_MYSQL_SESSION);
            if (session) session->active = FALSE;
            lua_pop(L, 1);
            pool_release_entry(op->pool, op->entry,
                               session && session->pool_ref != LUA_NOREF
                                   ? session->pool_ref : op->scope_ref,
                               TRUE);
            if (session) {
                if (session->pool_ref != LUA_NOREF)
                    luaL_unref(L, LUA_REGISTRYINDEX, session->pool_ref);
                session->pool_ref = LUA_NOREF;
                session->entry = NULL;
                session->pool = NULL;
            }
        }
        pool_invoke_operation_callback(op, absolute_value, error_message);
    }

    op->completed = TRUE;
    if (!op->dispatching) pool_free_op(op);
}

static int pool_operation_adapter(lua_State *L) {
    pool_op_t *op = (pool_op_t*)lua_touserdata(L, lua_upvalueindex(1));
    const char *error_message = lua_tostring(L, 3);
    int value_idx = lua_isnoneornil(L, 2) ? 0 : 2;
    pool_finish_operation(op, value_idx, error_message);
    return 0;
}

static void pool_start_operation(pool_op_t *op) {
    lua_State *L = op->L;
    int base = lua_gettop(L);
    int nargs;
    char *error_copy = NULL;
    op->dispatching = TRUE;
    if (op->kind == POOL_OP_EXECUTE_PREPARED) {
        lua_pushcfunction(L, l_mysql_execute_prepared_async);
        lua_rawgeti(L, LUA_REGISTRYINDEX, op->entry->connection_ref);
        lua_pushlstring(L, op->sql, op->sql_len);
        lua_rawgeti(L, LUA_REGISTRYINDEX, op->params_ref);
        lua_pushlightuserdata(L, op);
        lua_pushcclosure(L, pool_operation_adapter, 1);
        lua_pushnil(L);
        nargs = 5;
    } else if (op->kind == POOL_OP_PREPARE) {
        lua_pushcfunction(L, l_mysql_prepare_async);
        lua_rawgeti(L, LUA_REGISTRYINDEX, op->entry->connection_ref);
        lua_pushlstring(L, op->sql, op->sql_len);
        lua_pushlightuserdata(L, op);
        lua_pushcclosure(L, pool_operation_adapter, 1);
        lua_pushnil(L);
        nargs = 4;
    } else {
        lua_pushcfunction(L, l_mysql_exec_async);
        lua_rawgeti(L, LUA_REGISTRYINDEX, op->entry->connection_ref);
        lua_pushlstring(L, op->sql, op->sql_len);
        lua_pushlightuserdata(L, op);
        lua_pushcclosure(L, pool_operation_adapter, 1);
        lua_pushnil(L);
        nargs = 4;
    }
    if (lua_pcall(L, nargs, 2, 0) != 0)
        error_copy = g_strdup(lua_tostring(L, -1));
    else if (lua_isstring(L, -1))
        error_copy = g_strdup(lua_tostring(L, -1));
    lua_settop(L, base);
    op->dispatching = FALSE;
    if (error_copy && !op->completed)
        pool_finish_operation(op, 0, error_copy);
    g_free(error_copy);
    if (op->completed) pool_free_op(op);
}

static pool_op_t *new_pool_operation(lua_State *L, ps_mysql_pool_t *pool,
                                     pool_entry_t *entry,
                                     pool_op_kind_t kind,
                                     int callback_ref, int scope_ref,
                                     const char *sql, size_t sql_len,
                                     int params_ref,
                                     gboolean release_after) {
    pool_op_t *op = g_new0(pool_op_t, 1);
    op->L = L;
    op->pool = pool;
    op->entry = entry;
    op->kind = kind;
    op->callback_ref = callback_ref;
    op->scope_ref = scope_ref;
    op->params_ref = params_ref;
    op->sql = g_memdup2(sql, sql_len + 1);
    op->sql_len = sql_len;
    op->release_after = release_after;
    return op;
}

static void pool_start_job(pool_job_t *job, pool_entry_t *entry) {
    lua_State *L = job->pool->L;
    if (job->kind == POOL_JOB_ACQUIRE) {
        push_stored_callback(L, job->callback_ref, "func");
        lua_rawgeti(L, LUA_REGISTRYINDEX, job->pool_ref);
        push_new_session(L, job->pool, entry, job->pool_ref, FALSE);
        lua_pushnil(L);
        push_stored_callback(L, job->callback_ref, "dado");
        if (lua_pcall(L, 4, 0, 0) != 0) {
            g_printerr("adquiraAss\xC3\xADncrono retornou erro: %s\n",
                       lua_tostring(L, -1));
            lua_pop(L, 1);
        }
        pool_free_job(job);
        return;
    }

    entry->state = POOL_ENTRY_OPERATION;
    pool_op_kind_t kind = job->kind == POOL_JOB_BEGIN
                            ? POOL_OP_BEGIN
                            : (job->kind == POOL_JOB_EXECUTE_PREPARED
                                ? POOL_OP_EXECUTE_PREPARED
                                : POOL_OP_EXECUTE);
    const char *sql = job->kind == POOL_JOB_BEGIN
                        ? "START TRANSACTION" : job->sql;
    size_t sql_len = job->kind == POOL_JOB_BEGIN
                        ? strlen("START TRANSACTION") : job->sql_len;
    pool_op_t *op = new_pool_operation(L, job->pool, entry, kind,
                                        job->callback_ref, job->pool_ref,
                                        sql, sql_len, job->params_ref, TRUE);
    job->callback_ref = LUA_NOREF;
    job->pool_ref = LUA_NOREF;
    job->params_ref = LUA_NOREF;
    pool_free_job(job);
    pool_start_operation(op);
}

static int pool_submit_sql(lua_State *L, pool_job_kind_t kind,
                           int sql_idx, int params_idx,
                           int callback_idx, int data_idx) {
    ps_mysql_pool_t *pool = check_pool(L, 1);
    pool_job_t *job;
    size_t sql_len = 0;
    const char *sql;
    if (pool->closed) return push_nil_err(L, "piscina MariaDB fechada");
    if (!pool->ready) return push_nil_err(L, "piscina MariaDB ainda n\xC3\xA3o est\xC3\xA1 pronta");
    sql = luaL_checklstring(L, sql_idx, &sql_len);
    if (sql_len > ULONG_MAX) return push_nil_err(L, "comando SQL grande demais");
    if (params_idx) luaL_checktype(L, params_idx, LUA_TTABLE);
    luaL_checktype(L, callback_idx, LUA_TFUNCTION);
    if (!pool_find_entry(pool, POOL_ENTRY_FREE) &&
        pool_active_count(pool) >= pool->maximum &&
        (int)g_queue_get_length(pool->queue) >= pool->max_queue)
        return push_nil_err(L, "fila da piscina MariaDB cheia");
    job = new_pool_job(L, pool, kind, callback_idx, data_idx, 1);
    job->sql = g_memdup2(sql, sql_len + 1);
    job->sql_len = sql_len;
    if (params_idx) {
        lua_pushvalue(L, params_idx);
        job->params_ref = luaL_ref(L, LUA_REGISTRYINDEX);
    }
    pool_queue_job(job);
    return 0;
}

static int l_pool_execute_async(lua_State *L) {
    return pool_submit_sql(L, POOL_JOB_EXECUTE, 2, 0, 3, 4);
}

static int l_pool_execute_prepared_async(lua_State *L) {
    return pool_submit_sql(L, POOL_JOB_EXECUTE_PREPARED, 2, 3, 4, 5);
}

static int l_pool_begin_async(lua_State *L) {
    ps_mysql_pool_t *pool = check_pool(L, 1);
    pool_job_t *job;
    luaL_checktype(L, 2, LUA_TFUNCTION);
    if (pool->closed) return push_nil_err(L, "piscina MariaDB fechada");
    if (!pool->ready) return push_nil_err(L, "piscina MariaDB ainda n\xC3\xA3o est\xC3\xA1 pronta");
    if (!pool_find_entry(pool, POOL_ENTRY_FREE) &&
        pool_active_count(pool) >= pool->maximum &&
        (int)g_queue_get_length(pool->queue) >= pool->max_queue)
        return push_nil_err(L, "fila da piscina MariaDB cheia");
    job = new_pool_job(L, pool, POOL_JOB_BEGIN, 2, 3, 1);
    pool_queue_job(job);
    return 0;
}

static pool_op_t *new_scoped_operation(lua_State *L,
                                       ps_mysql_session_t *session,
                                       pool_op_kind_t kind,
                                       int sql_idx, int params_idx,
                                       int callback_idx, int data_idx) {
    size_t sql_len = 0;
    const char *sql = luaL_checklstring(L, sql_idx, &sql_len);
    int callback_ref, scope_ref, params_ref = LUA_NOREF;
    if (sql_len > ULONG_MAX) luaL_error(L, "comando SQL grande demais");
    if (params_idx) luaL_checktype(L, params_idx, LUA_TTABLE);
    luaL_checktype(L, callback_idx, LUA_TFUNCTION);
    callback_ref = store_callback(L, callback_idx, data_idx);
    lua_pushvalue(L, 1);
    scope_ref = luaL_ref(L, LUA_REGISTRYINDEX);
    if (params_idx) {
        lua_pushvalue(L, params_idx);
        params_ref = luaL_ref(L, LUA_REGISTRYINDEX);
    }
    return new_pool_operation(L, session->pool, session->entry, kind,
                              callback_ref, scope_ref, sql, sql_len,
                              params_ref, FALSE);
}

static int scoped_execute(lua_State *L, gboolean transaction,
                          pool_op_kind_t kind, int sql_idx, int params_idx,
                          int callback_idx, int data_idx) {
    ps_mysql_session_t *session = transaction ? check_transaction(L, 1)
                                              : check_session(L, 1);
    pool_op_t *op;
    if (!session_is_valid(session))
        return push_nil_err(L, transaction ? "transa\xC3\xA7\xC3\xA3o inativa"
                                           : "sess\xC3\xA3o inativa");
    if (session->entry->connection->busy)
        return push_nil_err(L, "conex\xC3\xA3o MariaDB ocupada");
    op = new_scoped_operation(L, session, kind, sql_idx, params_idx,
                              callback_idx, data_idx);
    pool_start_operation(op);
    return 0;
}

static int l_session_execute_async(lua_State *L) {
    return scoped_execute(L, FALSE, POOL_OP_EXECUTE, 2, 0, 3, 4);
}

static int l_session_execute_prepared_async(lua_State *L) {
    return scoped_execute(L, FALSE, POOL_OP_EXECUTE_PREPARED, 2, 3, 4, 5);
}

static int l_session_prepare_async(lua_State *L) {
    return scoped_execute(L, FALSE, POOL_OP_PREPARE, 2, 0, 3, 4);
}

static int l_transaction_execute_async(lua_State *L) {
    return scoped_execute(L, TRUE, POOL_OP_EXECUTE, 2, 0, 3, 4);
}

static int l_transaction_execute_prepared_async(lua_State *L) {
    return scoped_execute(L, TRUE, POOL_OP_EXECUTE_PREPARED, 2, 3, 4, 5);
}

static int l_transaction_prepare_async(lua_State *L) {
    return scoped_execute(L, TRUE, POOL_OP_PREPARE, 2, 0, 3, 4);
}

static int l_session_release(lua_State *L) {
    ps_mysql_session_t *session = check_session(L, 1);
    pool_entry_t *entry;
    int pool_ref;
    if (!session_is_valid(session)) return 0;
    entry = session->entry;
    if (!pool_entry_clean(entry))
        return push_nil_err(L, "feche opera\xC3\xA7\xC3\xB5" "es, resultados e consultas antes de devolver a sess\xC3\xA3o");
    pool_ref = session->pool_ref;
    session->active = FALSE;
    pool_release_entry(session->pool, entry, pool_ref,
                       pool_connection_broken(entry));
    luaL_unref(L, LUA_REGISTRYINDEX, session->pool_ref);
    session->pool_ref = LUA_NOREF;
    session->entry = NULL;
    session->pool = NULL;
    return 0;
}

static int l_session_gc(lua_State *L) {
    ps_mysql_session_t *session = check_session(L, 1);
    if (session_is_valid(session) && pool_entry_clean(session->entry)) {
        int pool_ref = session->pool_ref;
        session->active = FALSE;
        pool_release_entry(session->pool, session->entry, pool_ref, TRUE);
        luaL_unref(L, LUA_REGISTRYINDEX, session->pool_ref);
        session->pool_ref = LUA_NOREF;
        session->entry = NULL;
        session->pool = NULL;
    }
    return 0;
}

static int transaction_finalize(lua_State *L, pool_op_kind_t kind) {
    ps_mysql_session_t *transaction = check_transaction(L, 1);
    pool_op_t *op;
    const char *sql = kind == POOL_OP_COMMIT ? "COMMIT" : "ROLLBACK";
    if (!session_is_valid(transaction))
        return push_nil_err(L, "transa\xC3\xA7\xC3\xA3o inativa");
    if (!pool_entry_clean(transaction->entry))
        return push_nil_err(L, "feche opera\xC3\xA7\xC3\xB5" "es, resultados e consultas antes de finalizar a transa\xC3\xA7\xC3\xA3o");
    luaL_checktype(L, 2, LUA_TFUNCTION);
    int callback_ref = store_callback(L, 2, 3);
    lua_pushvalue(L, 1);
    int scope_ref = luaL_ref(L, LUA_REGISTRYINDEX);
    op = new_pool_operation(L, transaction->pool, transaction->entry,
                            kind, callback_ref, scope_ref,
                            sql, strlen(sql), LUA_NOREF, FALSE);
    pool_start_operation(op);
    return 0;
}

static int l_transaction_commit_async(lua_State *L) {
    return transaction_finalize(L, POOL_OP_COMMIT);
}

static int l_transaction_rollback_async(lua_State *L) {
    return transaction_finalize(L, POOL_OP_ROLLBACK);
}

static int l_transaction_gc(lua_State *L) {
    ps_mysql_session_t *transaction = check_transaction(L, 1);
    if (session_is_valid(transaction) && pool_entry_clean(transaction->entry)) {
        int pool_ref = transaction->pool_ref;
        transaction->active = FALSE;
        pool_release_entry(transaction->pool, transaction->entry,
                           pool_ref, TRUE);
        luaL_unref(L, LUA_REGISTRYINDEX, transaction->pool_ref);
        transaction->pool_ref = LUA_NOREF;
        transaction->entry = NULL;
        transaction->pool = NULL;
    }
    return 0;
}

/* ---------------- Registro ---------------- */

static const luaL_Reg pool_methods[] = {
    {"adquiraAss\xC3\xADncrono", l_pool_acquire_async},
    {"executeAss\xC3\xADncrono", l_pool_execute_async},
    {"executePreparadoAss\xC3\xADncrono", l_pool_execute_prepared_async},
    {"inicieTransa\xC3\xA7\xC3\xA3oAss\xC3\xADncrona", l_pool_begin_async},
    {"estado", l_pool_state},
    {"feche", l_pool_close},
    {LUA_MM_FINALIZE, l_pool_gc},
    {NULL, NULL}
};

static const luaL_Reg session_methods[] = {
    {"executeAss\xC3\xADncrono", l_session_execute_async},
    {"executePreparadoAss\xC3\xADncrono", l_session_execute_prepared_async},
    {"prepareConsultaAss\xC3\xADncrona", l_session_prepare_async},
    {"devolva", l_session_release},
    {LUA_MM_FINALIZE, l_session_gc},
    {NULL, NULL}
};

static const luaL_Reg transaction_methods[] = {
    {"executeAss\xC3\xADncrono", l_transaction_execute_async},
    {"executePreparadoAss\xC3\xADncrono", l_transaction_execute_prepared_async},
    {"prepareConsultaAss\xC3\xADncrona", l_transaction_prepare_async},
    {"confirmeAss\xC3\xADncrono", l_transaction_commit_async},
    {"desfa\xC3\xA7" "aAss\xC3\xADncrono", l_transaction_rollback_async},
    {LUA_MM_FINALIZE, l_transaction_gc},
    {NULL, NULL}
};

static const luaL_Reg con_methods[] = {
    {"executeAss\xC3\xADncrono", l_mysql_exec_async},
    {"executePreparadoAss\xC3\xADncrono", l_mysql_execute_prepared_async},
    {"prepareConsultaAss\xC3\xADncrona", l_mysql_prepare_async},
    {"escapeColar", l_mysql_escape_string},
    {"feche", l_mysql_close},
    {LUA_MM_FINALIZE, l_mysql_gc},
    {NULL, NULL}
};

static const luaL_Reg stmt_methods[] = {
    {"executeAss\xC3\xADncrono", l_stmt_execute_async},
    {"n\xC3\xBAmeroDePar\xC3\xA2metros", l_stmt_param_count},
    {"feche", l_stmt_close},
    {LUA_MM_FINALIZE, l_stmt_gc},
    {NULL, NULL}
};

static const luaL_Reg res_methods[] = {
    {"obterLinha", l_res_fetch_row},
    {"n\xC3\xBAmeroDeLinhas", l_res_num_rows},
    {"linhasAfetadas", l_res_affected_rows},
    {"idInserido", l_res_insert_id},
    {"feche", l_res_close},
    {LUA_MM_FINALIZE, l_res_close},
    {NULL, NULL}
};

static const luaL_Reg mysql_funcs[] = {
    {"conecteAss\xC3\xADncrono", l_mysql_conecte_async},
    {"criePiscinaAss\xC3\xADncrona", l_mysql_create_pool_async},
    {"vers\xC3\xA3oDoConector", l_mysql_info},
    {NULL, NULL}
};

LUA_API int luaopen_mariadb(lua_State *L) {
    mysql_library_init(0, NULL, NULL);
    if (luaL_newmetatable(L, PS_MYSQL_CON)) {
        luaL_setfuncs(L, con_methods, 0);
        lua_pushvalue(L, -1); lua_setfield(L, -2, LUA_MM_INDICE);
    } lua_pop(L, 1);
    if (luaL_newmetatable(L, PS_MYSQL_RES)) {
        luaL_setfuncs(L, res_methods, 0);
        lua_pushvalue(L, -1); lua_setfield(L, -2, LUA_MM_INDICE);
    } lua_pop(L, 1);
    if (luaL_newmetatable(L, PS_MYSQL_STMT)) {
        luaL_setfuncs(L, stmt_methods, 0);
        lua_pushvalue(L, -1); lua_setfield(L, -2, LUA_MM_INDICE);
    } lua_pop(L, 1);
    if (luaL_newmetatable(L, PS_MYSQL_POOL)) {
        luaL_setfuncs(L, pool_methods, 0);
        lua_pushvalue(L, -1); lua_setfield(L, -2, LUA_MM_INDICE);
    } lua_pop(L, 1);
    if (luaL_newmetatable(L, PS_MYSQL_SESSION)) {
        luaL_setfuncs(L, session_methods, 0);
        lua_pushvalue(L, -1); lua_setfield(L, -2, LUA_MM_INDICE);
    } lua_pop(L, 1);
    if (luaL_newmetatable(L, PS_MYSQL_TRANSACTION)) {
        luaL_setfuncs(L, transaction_methods, 0);
        lua_pushvalue(L, -1); lua_setfield(L, -2, LUA_MM_INDICE);
    } lua_pop(L, 1);
    luaL_newlib(L, mysql_funcs);
    return 1;
}
