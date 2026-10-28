#!/bin/sh
set -eu
base=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
test -f "$base/.laboratorio-dados3" || { echo 'Use somente a árvore gerada por preparar.py' >&2; exit 1; }
cd "$base"
mkdir -p evidencias
cp ferramentas/sls/nativo.c src/sls_nativo.c
flags='-DSANTAFE_DADOS_EXPERIMENTAL -DSANTAFE_SLS_EMBUTIDO -DLUA_USE_APICHECK -DLUA_USE_POSIX -DLUA_USE_DLOPEN'
case $(uname -s) in
  Darwin) libs=''; link='-Wl,-export_dynamic' ;;
  Linux) libs='-ldl -lcrypto'; link='-Wl,-E' ;;
  *) echo 'Plataforma não homologada' >&2; exit 1 ;;
esac
make -C src -j2 generic MYCFLAGS="$flags" MYLIBS="$libs" MYLDFLAGS="$link" MYOBJS=sls_nativo.o
for lib in arquivo rede mariadb segredo tomada; do
  make -C "bibs/bibc/$lib" -j2 CC='cc -DSANTAFE_DADOS_EXPERIMENTAL -DLUA_USE_APICHECK'
done
./src/santafé -E -P -v
