// bombardeia_http.c
// Ferramenta simples de carga HTTP para testar o servidor Santafe + rede + mariadb
// Uso: ./bombardeia_http 127.0.0.1 7000 /usuarios 10 100
//      (10 threads, 100 requisições por thread)

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <pthread.h>
#include <errno.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netdb.h>

typedef struct {
    char host[256];
    char port[16];
    char path[256];
    int  requests_per_thread;
} worker_args_t;

static volatile long total_ok    = 0;
static volatile long total_fail  = 0;

static void *worker_thread(void *arg) {
    worker_args_t *w = (worker_args_t*)arg;

    char req[512];
    snprintf(req, sizeof(req),
             "GET %s HTTP/1.1\r\n"
             "Host: %s\r\n"
             "Connection: close\r\n"
             "\r\n",
             w->path, w->host);

    struct addrinfo hints;
    struct addrinfo *res = NULL;

    memset(&hints, 0, sizeof(hints));
    hints.ai_family   = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;

    int err = getaddrinfo(w->host, w->port, &hints, &res);
    if (err != 0) {
        fprintf(stderr, "getaddrinfo: %s\n", gai_strerror(err));
        return NULL;
    }

    for (int i = 0; i < w->requests_per_thread; i++) {
        int sock = socket(res->ai_family, res->ai_socktype, res->ai_protocol);
        if (sock < 0) {
            __sync_fetch_and_add(&total_fail, 1);
            continue;
        }

        if (connect(sock, res->ai_addr, res->ai_addrlen) < 0) {
            __sync_fetch_and_add(&total_fail, 1);
            close(sock);
            continue;
        }

        ssize_t sent = send(sock, req, strlen(req), 0);
        if (sent <= 0) {
            __sync_fetch_and_add(&total_fail, 1);
            close(sock);
            continue;
        }

        // leitura simples de toda a resposta e descarte
        char buf[4096];
        ssize_t n;
        int ok = 0;

        while ((n = recv(sock, buf, sizeof(buf), 0)) > 0) {
            // checa se a resposta contem "200" (muito simples, mas suficiente para teste)
            if (!ok && n >= 12) {
                // Procurar " 200 " na linha de status
                for (ssize_t j = 0; j < n - 4; j++) {
                    if (buf[j] == ' ' && buf[j+1] == '2' && buf[j+2] == '0' && buf[j+3] == '0' && buf[j+4] == ' ') {
                        ok = 1;
                        break;
                    }
                }
            }
        }

        if (ok) {
            __sync_fetch_and_add(&total_ok, 1);
        } else {
            __sync_fetch_and_add(&total_fail, 1);
        }

        close(sock);
    }

    freeaddrinfo(res);
    return NULL;
}

int main(int argc, char **argv) {
    if (argc != 6) {
        fprintf(stderr, "Uso: %s host porta caminho threads req_por_thread\n", argv[0]);
        fprintf(stderr, "Exemplo: %s 127.0.0.1 7000 /usuarios 10 100\n", argv[0]);
        return 1;
    }

    const char *host  = argv[1];
    const char *port  = argv[2];
    const char *path  = argv[3];
    int threads       = atoi(argv[4]);
    int req_per_thr   = atoi(argv[5]);

    if (threads <= 0 || req_per_thr <= 0) {
        fprintf(stderr, "threads e req_por_thread devem ser > 0\n");
        return 1;
    }

    pthread_t *tids = calloc(threads, sizeof(pthread_t));
    if (!tids) {
        perror("calloc");
        return 1;
    }

    worker_args_t wargs;
    memset(&wargs, 0, sizeof(wargs));
    snprintf(wargs.host, sizeof(wargs.host), "%s", host);
    snprintf(wargs.port, sizeof(wargs.port), "%s", port);
    snprintf(wargs.path, sizeof(wargs.path), "%s", path);
    wargs.requests_per_thread = req_per_thr;

    for (int i = 0; i < threads; i++) {
        if (pthread_create(&tids[i], NULL, worker_thread, &wargs) != 0) {
            perror("pthread_create");
            free(tids);
            return 1;
        }
    }

    for (int i = 0; i < threads; i++) {
        pthread_join(tids[i], NULL);
    }

    printf("Total OK   : %ld\n", total_ok);
    printf("Total FAIL : %ld\n", total_fail);
    printf("Total REQ  : %ld\n", total_ok + total_fail);

    free(tids);
    return 0;
}
