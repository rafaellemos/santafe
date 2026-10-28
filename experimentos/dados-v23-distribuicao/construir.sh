#!/bin/sh
set -eu
base=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
test -f "$base/.laboratorio-dados23"
cd "$base"
# Nenhuma opção experimental: o contrato deve vir do cabeçalho do SDK.
cp ferramentas/sls/nativo.c src/sls_nativo.c
case $(uname -s) in
  Darwin) libs=''; link='-Wl,-export_dynamic' ;;
  Linux) libs='-ldl -lcrypto'; link='-Wl,-E' ;;
  *) echo 'Use a receita Windows para Windows nativo.' >&2; exit 1 ;;
esac
make -C src -j2 generic MYCFLAGS='-DSANTAFE_SLS_EMBUTIDO -DLUA_USE_APICHECK -DLUA_USE_POSIX -DLUA_USE_DLOPEN' MYLIBS="$libs" MYLDFLAGS="$link" MYOBJS=sls_nativo.o
for lib in arquivo rede mariadb segredo tomada; do
  make -C "bibs/bibc/$lib" -j2 CC='cc -DLUA_USE_APICHECK'
done
make -C ferramentas/sls CFLAGS='-O2 -Wall -Wextra -DLUA_USE_APICHECK'
make -C ferramentas/pacotes CFLAGS='-O2 -Wall -Wextra -DLUA_USE_APICHECK'
./src/santafé -E -P -v
