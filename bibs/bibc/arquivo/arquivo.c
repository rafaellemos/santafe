/*
 * arquivo.c — entrada e saída assíncrona de arquivos para Santafé.
 *
 * As operações bloqueantes rodam na piscina de trabalho do GLib. O tratador
 * volta ao contexto principal do GIO, portanto pode interagir com a VM sem
 * concorrer com outra linha de execução.
 */

#define _POSIX_C_SOURCE 200809L

#include <gio/gio.h>
#include <glib.h>
#include <glib/gstdio.h>
#include <errno.h>
#include <fcntl.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#include "lua.h"
#include "lauxlib.h"

#ifndef O_CLOEXEC
#define O_CLOEXEC 0
#endif

typedef enum {
    ARQ_LEIA,
    ARQ_GRAVE_DURAVEL,
    ARQ_MOVA,
    ARQ_REMOVA,
    ARQ_CRIE_DIRETORIOS,
    ARQ_EXISTE
} arq_operacao_t;

typedef struct {
    lua_State *L;
    int tratador_ref;
    int dado_ref;
    arq_operacao_t operacao;
    char *caminho;
    char *destino;
    unsigned char *conteudo;
    gsize tamanho;
    gsize limite;
    unsigned char *leitura;
    gsize leitura_tamanho;
    gboolean lógico;
    mode_t permissões;
    gboolean aplique_permissões;
} arq_tarefa_t;

static void arq_libere(arq_tarefa_t *tarefa) {
    if (!tarefa) return;
    if (tarefa->L) {
        luaL_unref(tarefa->L, LUA_REGISTRYINDEX, tarefa->tratador_ref);
        if (tarefa->dado_ref != LUA_NOREF)
            luaL_unref(tarefa->L, LUA_REGISTRYINDEX, tarefa->dado_ref);
    }
    g_free(tarefa->caminho);
    g_free(tarefa->destino);
    g_free(tarefa->conteudo);
    g_free(tarefa->leitura);
    g_free(tarefa);
}

static void arq_falhe_errno(GTask *task, const char *ação, const char *caminho) {
    int código = errno;
    g_task_return_new_error(task, G_IO_ERROR, g_io_error_from_errno(código),
                            "%s '%s': %s", ação, caminho, g_strerror(código));
}

static gboolean arq_escreva_tudo(int fd, const unsigned char *dados,
                                 gsize tamanho) {
    gsize gravado = 0;
    while (gravado < tamanho) {
        ssize_t n = write(fd, dados + gravado, tamanho - gravado);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) return FALSE;
        gravado += (gsize)n;
    }
    return TRUE;
}

static gboolean arq_sincronize(int fd) {
#if defined(__APPLE__) && defined(F_FULLFSYNC)
    if (fcntl(fd, F_FULLFSYNC) == 0) return TRUE;
#endif
    return fsync(fd) == 0;
}

static void arq_grave_durável(GTask *task, arq_tarefa_t *tarefa) {
    char *diretório = g_path_get_dirname(tarefa->caminho);
    char *nome = g_path_get_basename(tarefa->caminho);
    char *temporário = g_strdup_printf("%s/.%s.XXXXXX", diretório, nome);
    int fd = g_mkstemp_full(temporário, O_RDWR | O_CLOEXEC,
                            tarefa->permissões);
    if (fd < 0) {
        arq_falhe_errno(task, "não foi possível criar o temporário de", tarefa->caminho);
        goto fim;
    }
    if (fchmod(fd, tarefa->permissões) != 0) {
        arq_falhe_errno(task, "não foi possível definir as permissões de",
                        tarefa->caminho);
        close(fd); g_remove(temporário); goto fim;
    }
    if (!arq_escreva_tudo(fd, tarefa->conteudo, tarefa->tamanho)) {
        arq_falhe_errno(task, "não foi possível gravar", tarefa->caminho);
        close(fd); g_remove(temporário); goto fim;
    }
    if (!arq_sincronize(fd)) {
        arq_falhe_errno(task, "não foi possível sincronizar", tarefa->caminho);
        close(fd); g_remove(temporário); goto fim;
    }
    if (close(fd) != 0) {
        arq_falhe_errno(task, "não foi possível fechar", tarefa->caminho);
        g_remove(temporário); goto fim;
    }
    if (g_rename(temporário, tarefa->caminho) != 0) {
        arq_falhe_errno(task, "não foi possível publicar", tarefa->caminho);
        g_remove(temporário); goto fim;
    }
    {
        int dfd = open(diretório, O_RDONLY | O_CLOEXEC);
        if (dfd < 0) {
            arq_falhe_errno(task, "não foi possível abrir o diretório", diretório);
            goto fim;
        }
        if (!arq_sincronize(dfd)) {
            arq_falhe_errno(task, "não foi possível sincronizar o diretório", diretório);
            close(dfd);
            goto fim;
        }
        close(dfd);
    }
    g_task_return_boolean(task, TRUE);

fim:
    g_free(temporário);
    g_free(nome);
    g_free(diretório);
}

static void arq_leia(GTask *task, arq_tarefa_t *tarefa) {
    int fd = open(tarefa->caminho, O_RDONLY | O_CLOEXEC);
    struct stat estado;
    gsize usado = 0;
    if (fd < 0) {
        arq_falhe_errno(task, "não foi possível abrir", tarefa->caminho);
        return;
    }
    if (fstat(fd, &estado) != 0) {
        arq_falhe_errno(task, "não foi possível medir", tarefa->caminho);
        close(fd); return;
    }
    if (estado.st_size < 0 || (guint64)estado.st_size > tarefa->limite) {
        g_task_return_new_error(task, G_IO_ERROR, G_IO_ERROR_FAILED,
            "arquivo excede o limite de %" G_GSIZE_FORMAT " tacos", tarefa->limite);
        close(fd); return;
    }
    tarefa->leitura = g_malloc((gsize)estado.st_size + 1);
    while (usado < (gsize)estado.st_size) {
        ssize_t n = read(fd, tarefa->leitura + usado, (gsize)estado.st_size - usado);
        if (n < 0 && errno == EINTR) continue;
        if (n < 0) {
            arq_falhe_errno(task, "não foi possível ler", tarefa->caminho);
            close(fd); return;
        }
        if (n == 0) break;
        usado += (gsize)n;
    }
    close(fd);
    tarefa->leitura[usado] = '\0';
    tarefa->leitura_tamanho = usado;
    g_task_return_boolean(task, TRUE);
}

static void arq_trabalhe(GTask *task, gpointer origem, gpointer dados,
                         GCancellable *cancelável) {
    arq_tarefa_t *tarefa = (arq_tarefa_t *)dados;
    (void)origem; (void)cancelável;
    switch (tarefa->operacao) {
        case ARQ_LEIA:
            arq_leia(task, tarefa);
            return;
        case ARQ_GRAVE_DURAVEL:
            arq_grave_durável(task, tarefa);
            return;
        case ARQ_MOVA:
            if (g_rename(tarefa->caminho, tarefa->destino) != 0) {
                arq_falhe_errno(task, "não foi possível mover", tarefa->caminho);
                return;
            }
            g_task_return_boolean(task, TRUE);
            return;
        case ARQ_REMOVA:
            if (g_remove(tarefa->caminho) != 0 && errno != ENOENT) {
                arq_falhe_errno(task, "não foi possível remover", tarefa->caminho);
                return;
            }
            g_task_return_boolean(task, TRUE);
            return;
        case ARQ_CRIE_DIRETORIOS:
        {
            struct stat estado_antes;
            gboolean existia = FALSE;

            if (stat(tarefa->caminho, &estado_antes) == 0) {
                if (!S_ISDIR(estado_antes.st_mode)) {
                    g_task_return_new_error(task, G_IO_ERROR,
                                            G_IO_ERROR_NOT_DIRECTORY,
                                            "o caminho '%s' existe e não é um diretório",
                                            tarefa->caminho);
                    return;
                }
                existia = TRUE;
            } else if (errno != ENOENT) {
                arq_falhe_errno(task, "não foi possível consultar o diretório",
                                tarefa->caminho);
                return;
            }
            if (g_mkdir_with_parents(tarefa->caminho,
                                     tarefa->permissões) != 0) {
                arq_falhe_errno(task, "não foi possível criar o diretório", tarefa->caminho);
                return;
            }
            /*
             * Um diretório compartilhado pode pertencer a outro processo do
             * mesmo grupo. Nesse caso ele já está pronto para uso, mas o
             * processo atual não tem autoridade para executar chmod(2).
             * Preserve as permissões existentes e aplique o modo solicitado
             * somente ao diretório que esta operação realmente criou.
             */
            if (tarefa->aplique_permissões && !existia &&
                g_chmod(tarefa->caminho, tarefa->permissões) != 0) {
                arq_falhe_errno(task, "não foi possível definir as permissões do diretório",
                                tarefa->caminho);
                return;
            }
            g_task_return_boolean(task, TRUE);
            return;
        }
        case ARQ_EXISTE: {
            struct stat estado;
            if (stat(tarefa->caminho, &estado) == 0) tarefa->lógico = TRUE;
            else if (errno == ENOENT) tarefa->lógico = FALSE;
            else {
                arq_falhe_errno(task, "não foi possível consultar", tarefa->caminho);
                return;
            }
            g_task_return_boolean(task, TRUE);
            return;
        }
    }
    g_task_return_new_error(task, G_IO_ERROR, G_IO_ERROR_FAILED,
                            "operação de arquivo desconhecida");
}

static void arq_conclua(GObject *origem, GAsyncResult *resultado, gpointer dados) {
    arq_tarefa_t *tarefa = (arq_tarefa_t *)dados;
    GError *erro = NULL;
    gboolean funcionou = g_task_propagate_boolean(G_TASK(resultado), &erro);
    lua_State *L = tarefa->L;
    int base = lua_gettop(L);
    (void)origem;

    lua_rawgeti(L, LUA_REGISTRYINDEX, tarefa->tratador_ref);
    if (funcionou) {
        if (tarefa->operacao == ARQ_LEIA)
            lua_pushlstring(L, (const char *)tarefa->leitura, tarefa->leitura_tamanho);
        else if (tarefa->operacao == ARQ_EXISTE)
            lua_pushboolean(L, tarefa->lógico);
        else
            lua_pushboolean(L, 1);
        lua_pushnil(L);
    } else {
        lua_pushnil(L);
        lua_pushstring(L, erro ? erro->message : "falha de arquivo");
    }
    if (tarefa->dado_ref != LUA_NOREF)
        lua_rawgeti(L, LUA_REGISTRYINDEX, tarefa->dado_ref);
    else
        lua_pushnil(L);

    if (lua_pcall(L, 3, 0, 0) != LUA_OK) {
        const char *mensagem = lua_tostring(L, -1);
        g_printerr("[arquivo] falha no tratador: %s\n",
                   mensagem ? mensagem : "erro desconhecido");
        lua_pop(L, 1);
    }
    lua_settop(L, base);
    if (erro) g_error_free(erro);
    arq_libere(tarefa);
}

static const char *arq_valide_caminho(lua_State *L, int índice,
                                      size_t *tamanho) {
    const char *texto = luaL_checklstring(L, índice, tamanho);
    luaL_argcheck(L, *tamanho > 0 && memchr(texto, '\0', *tamanho) == NULL,
                  índice, "caminho inválido");
    return texto;
}

static arq_tarefa_t *arq_nova_tarefa(lua_State *L, arq_operacao_t operação,
                                     int tratador, int dado) {
    arq_tarefa_t *tarefa;
    luaL_checktype(L, tratador, LUA_TFUNCTION);
    tarefa = g_new0(arq_tarefa_t, 1);
    tarefa->L = L;
    tarefa->operacao = operação;
    lua_pushvalue(L, tratador);
    tarefa->tratador_ref = luaL_ref(L, LUA_REGISTRYINDEX);
    tarefa->dado_ref = LUA_NOREF;
    if (!lua_isnoneornil(L, dado)) {
        lua_pushvalue(L, dado);
        tarefa->dado_ref = luaL_ref(L, LUA_REGISTRYINDEX);
    }
    return tarefa;
}

static int arq_agende(lua_State *L, arq_tarefa_t *tarefa) {
    GTask *task = g_task_new(NULL, NULL, arq_conclua, tarefa);
    g_task_set_task_data(task, tarefa, NULL);
    g_task_run_in_thread(task, arq_trabalhe);
    g_object_unref(task);
    lua_pushboolean(L, 1);
    return 1;
}

static int l_arq_leia(lua_State *L) {
    lua_Integer limite = luaL_optinteger(L, 2, 64 * 1024 * 1024);
    size_t caminho_tamanho = 0;
    const char *caminho;
    arq_tarefa_t *tarefa;
    luaL_argcheck(L, limite >= 0 && (guint64)limite <= G_MAXSIZE, 2,
                  "limite inválido");
    caminho = arq_valide_caminho(L, 1, &caminho_tamanho);
    luaL_checktype(L, 3, LUA_TFUNCTION);
    tarefa = arq_nova_tarefa(L, ARQ_LEIA, 3, 4);
    tarefa->caminho = g_strndup(caminho, caminho_tamanho);
    tarefa->limite = (gsize)limite;
    return arq_agende(L, tarefa);
}

static int l_arq_grave_durável(lua_State *L) {
    size_t tamanho = 0;
    size_t caminho_tamanho = 0;
    const char *conteúdo = luaL_checklstring(L, 2, &tamanho);
    const char *caminho = arq_valide_caminho(L, 1, &caminho_tamanho);
    luaL_checktype(L, 3, LUA_TFUNCTION);
    arq_tarefa_t *tarefa = arq_nova_tarefa(L, ARQ_GRAVE_DURAVEL, 3, 4);
    tarefa->caminho = g_strndup(caminho, caminho_tamanho);
    tarefa->conteudo = g_malloc(tamanho ? tamanho : 1);
    if (tamanho) memcpy(tarefa->conteudo, conteúdo, tamanho);
    tarefa->tamanho = tamanho;
    tarefa->permissões = 0600;
    return arq_agende(L, tarefa);
}

static int l_arq_grave_durável_com_permissões(lua_State *L) {
    size_t tamanho = 0;
    size_t caminho_tamanho = 0;
    const char *conteúdo = luaL_checklstring(L, 2, &tamanho);
    lua_Integer permissões = luaL_checkinteger(L, 3);
    const char *caminho = arq_valide_caminho(L, 1, &caminho_tamanho);
    arq_tarefa_t *tarefa;
    luaL_argcheck(L, permissões >= 0 && permissões <= 0777, 3,
                  "permissões de arquivo inválidas");
    luaL_checktype(L, 4, LUA_TFUNCTION);
    tarefa = arq_nova_tarefa(L, ARQ_GRAVE_DURAVEL, 4, 5);
    tarefa->caminho = g_strndup(caminho, caminho_tamanho);
    tarefa->conteudo = g_malloc(tamanho ? tamanho : 1);
    if (tamanho) memcpy(tarefa->conteudo, conteúdo, tamanho);
    tarefa->tamanho = tamanho;
    tarefa->permissões = (mode_t)permissões;
    return arq_agende(L, tarefa);
}

static int l_arq_mova(lua_State *L) {
    size_t caminho_tamanho = 0;
    size_t destino_tamanho = 0;
    const char *caminho = arq_valide_caminho(L, 1, &caminho_tamanho);
    const char *destino = arq_valide_caminho(L, 2, &destino_tamanho);
    luaL_checktype(L, 3, LUA_TFUNCTION);
    arq_tarefa_t *tarefa = arq_nova_tarefa(L, ARQ_MOVA, 3, 4);
    tarefa->caminho = g_strndup(caminho, caminho_tamanho);
    tarefa->destino = g_strndup(destino, destino_tamanho);
    return arq_agende(L, tarefa);
}

static int l_arq_remova(lua_State *L) {
    size_t caminho_tamanho = 0;
    const char *caminho = arq_valide_caminho(L, 1, &caminho_tamanho);
    luaL_checktype(L, 2, LUA_TFUNCTION);
    arq_tarefa_t *tarefa = arq_nova_tarefa(L, ARQ_REMOVA, 2, 3);
    tarefa->caminho = g_strndup(caminho, caminho_tamanho);
    return arq_agende(L, tarefa);
}

static int l_arq_crie_diretórios(lua_State *L) {
    size_t caminho_tamanho = 0;
    const char *caminho = arq_valide_caminho(L, 1, &caminho_tamanho);
    luaL_checktype(L, 2, LUA_TFUNCTION);
    arq_tarefa_t *tarefa = arq_nova_tarefa(L, ARQ_CRIE_DIRETORIOS, 2, 3);
    tarefa->caminho = g_strndup(caminho, caminho_tamanho);
    tarefa->permissões = 0700;
    return arq_agende(L, tarefa);
}

static int l_arq_crie_diretórios_com_permissões(lua_State *L) {
    size_t caminho_tamanho = 0;
    const char *caminho = arq_valide_caminho(L, 1, &caminho_tamanho);
    lua_Integer permissões = luaL_checkinteger(L, 2);
    arq_tarefa_t *tarefa;
    luaL_argcheck(L, permissões >= 0 && permissões <= 07777, 2,
                  "permissões de diretório inválidas");
    luaL_checktype(L, 3, LUA_TFUNCTION);
    tarefa = arq_nova_tarefa(L, ARQ_CRIE_DIRETORIOS, 3, 4);
    tarefa->caminho = g_strndup(caminho, caminho_tamanho);
    tarefa->permissões = (mode_t)permissões;
    tarefa->aplique_permissões = TRUE;
    return arq_agende(L, tarefa);
}

static int l_arq_existe(lua_State *L) {
    size_t caminho_tamanho = 0;
    const char *caminho = arq_valide_caminho(L, 1, &caminho_tamanho);
    luaL_checktype(L, 2, LUA_TFUNCTION);
    arq_tarefa_t *tarefa = arq_nova_tarefa(L, ARQ_EXISTE, 2, 3);
    tarefa->caminho = g_strndup(caminho, caminho_tamanho);
    return arq_agende(L, tarefa);
}

static const luaL_Reg arquivo_funções[] = {
    {"leiaAss\xC3\xADncrono", l_arq_leia},
    {"graveDur\xC3\xA1velAss\xC3\xADncrono", l_arq_grave_durável},
    {"graveDur\xC3\xA1velComPermiss\xC3\xB5" "esAss\xC3\xADncrono",
     l_arq_grave_durável_com_permissões},
    {"movaAss\xC3\xADncrono", l_arq_mova},
    {"removaAss\xC3\xADncrono", l_arq_remova},
    {"crieDiret\xC3\xB3riosAss\xC3\xADncrono", l_arq_crie_diretórios},
    {"crieDiret\xC3\xB3riosComPermiss\xC3\xB5" "esAss\xC3\xADncrono",
     l_arq_crie_diretórios_com_permissões},
    {"existeAss\xC3\xADncrono", l_arq_existe},
    {NULL, NULL}
};

int luaopen_arquivo(lua_State *L) {
    luaL_newlib(L, arquivo_funções);
    return 1;
}
