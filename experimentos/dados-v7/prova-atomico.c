/* Executável de testes separado: os ganchos nunca entram no módulo instalado. */
#define _POSIX_C_SOURCE 200809L
#ifdef __APPLE__
#define _DARWIN_C_SOURCE 1
#endif
#include <glib.h>
#include <stdio.h>
#include <errno.h>
#include <fcntl.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>
static const char *modo;
static const char *destino;
static int escritas;
int arq_atomo_teste(const char *etapa) {
    if (!strcmp(modo,etapa)) { errno=EIO; return 1; }
    if (!strcmp(modo,"crash-antes") && !strcmp(etapa,"antes-troca")) _exit(91);
    if (!strcmp(modo,"crash-depois") && !strcmp(etapa,"depois-troca")) _exit(92);
    if (!strcmp(modo,"mudar-pai") && !strcmp(etapa,"antes-troca")) {
        char *pai=g_path_get_dirname(destino), *novo=g_strconcat(pai,"-movido",NULL);
        if (rename(pai,novo)!=0 || mkdir(pai,0700)!=0) _exit(93);
        g_free(pai);g_free(novo);
    }
    return 0;
}
static ssize_t escrita_teste(int fd,const void *s,size_t n) {
    escritas++;
    if (!strcmp(modo,"curta-eintr") && escritas==1) { errno=EINTR;return -1; }
    if (!strcmp(modo,"parcial-enospc") && escritas>1) { errno=ENOSPC;return -1; }
    if (!strcmp(modo,"zero")) return 0;
    if (!strcmp(modo,"curta-eintr") || !strcmp(modo,"parcial-enospc")) n=MIN(n,7);
    return write(fd,s,n);
}
#define write escrita_teste
#define ARQ_ATOMICO_TESTE 1
#include "atomico.h"
int main(int argc,char **argv) {
    if (argc!=4) return 2;
    destino=argv[1];modo=argv[2];
    at_resultado r=at_grave(destino,(unsigned char *)argv[3],strlen(argv[3]));
    printf("%d %d %s\n",r.erro,r.estado,at_estado(r));
    return 0;
}
