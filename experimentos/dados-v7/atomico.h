/* Persistência POSIX compartilhada pelos caminhos síncrono e assíncrono.
 * Diretório pai confiável, resolvido uma vez; NÃO é uma sandbox de caminhos.
 * O estado é independente do errno: depois de renameat não há rollback implícito.
 */
#include <stdio.h>

typedef struct { int erro; int estado; const char *etapa; } at_resultado;
/* estado: 0=inalterado, 1=publicado, 2=durável */
#ifdef ARQ_ATOMICO_TESTE
extern int arq_atomo_teste(const char *etapa);
#define AT_FALHA(etapa) arq_atomo_teste(etapa)
#else
#define AT_FALHA(etapa) 0
#endif

static int at_sync(int fd) {
#if defined(__APPLE__) && defined(F_FULLFSYNC)
    if (fcntl(fd, F_FULLFSYNC) == 0) return 0;
#endif
    int r;
    do { r = fsync(fd); } while (r < 0 && errno == EINTR);
    return r;
}

static int at_regular(int dir, const char *nome) {
    struct stat st;
    if (fstatat(dir, nome, &st, AT_SYMLINK_NOFOLLOW) == 0) {
        if (S_ISREG(st.st_mode)) return 0;
        errno = EINVAL; return -1;
    }
    return errno == ENOENT ? 0 : -1;
}

static at_resultado at_grave(const char *caminho, const unsigned char *dados, size_t tamanho) {
    at_resultado r = {0, 0, "caminho"};
    int dir = -1, fd = -1, criado = 0;
    char *pai = g_path_get_dirname(caminho), *nome = g_path_get_basename(caminho);
    char temp[80] = {0};
    if (!*caminho || caminho[strlen(caminho)-1] == '/' ||
        !strcmp(nome,".") || !strcmp(nome,"..")) { errno=EINVAL; goto falha; }
    r.etapa = "diretório";
    dir = open(pai, O_RDONLY | O_DIRECTORY | O_CLOEXEC);
    if (dir < 0) goto falha;
    r.etapa = "destino regular";
    if (at_regular(dir,nome) < 0) goto falha;
    r.etapa = "temporário";
    for (int i=0; i<8; i++) {
        char *uuid = g_uuid_string_random();
        g_snprintf(temp,sizeof temp,".onfe-%s.tmp",uuid); g_free(uuid);
        if (AT_FALHA("criar")) goto falha;
        fd = openat(dir,temp,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0600);
        if (fd >= 0) { criado=1; break; }
        if (errno != EEXIST) goto falha;
    }
    if (fd < 0) goto falha;
    r.etapa = "permissões";
    if (AT_FALHA("permissoes") || fchmod(fd,0600) != 0) goto falha;
    r.etapa = "escrita";
    size_t pos=0;
    while (pos<tamanho) {
        if (AT_FALHA("escrever")) goto falha;
        ssize_t n=write(fd,dados+pos,tamanho-pos);
        if (n<0 && errno==EINTR) continue;
        if (n<=0) { if (n==0) errno=EIO; goto falha; }
        pos+=(size_t)n;
    }
    r.etapa = "sincronização do arquivo";
    if (AT_FALHA("sincronizar-arquivo") || at_sync(fd) != 0) goto falha;
    r.etapa = "fechamento";
    { int fechado=close(fd); fd=-1;
      if (AT_FALHA("fechar") || fechado != 0) goto falha; }
    r.etapa = "troca";
    if (AT_FALHA("antes-troca") || at_regular(dir,nome)<0 ||
        AT_FALHA("renomear") || renameat(dir,temp,dir,nome)!=0) goto falha;
    criado=0; r.estado=1;
    r.etapa = "sincronização do diretório";
    if (AT_FALHA("depois-troca") || AT_FALHA("sincronizar-diretorio") || at_sync(dir)!=0) goto falha;
    r.estado=2; r.etapa="concluído";
    goto fim;
falha:
    r.erro=errno ? errno : EIO;
fim:
    if (fd>=0) close(fd);
    if (criado) unlinkat(dir,temp,0);
    if (dir>=0) close(dir);
    g_free(pai); g_free(nome);
    return r;
}

static const char *at_estado(at_resultado r) {
    return r.estado==2 ? "durável" : r.estado==1 ? "publicado" : "inalterado";
}
