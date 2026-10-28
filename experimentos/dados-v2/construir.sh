#!/bin/sh
# Isolado: nenhuma instalação, .so de produção ou objetos do checkout.
set -eu
base=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
destino="$base/dist/candidato-dados-v2"
opcoes='-DSANTAFE_DADOS_EXPERIMENTAL -DSANTAFE_SLS_EMBUTIDO -DLUA_USE_APICHECK'
ligacao=''
case "${1:-normal}" in
  normal) ;;
  estavel) destino="$destino-baseline"; opcoes='-DSANTAFE_SLS_EMBUTIDO -DLUA_USE_APICHECK' ;;
  sanitizado) destino="$destino-sanitizado"; opcoes="$opcoes -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer"; ligacao='-fsanitize=address,undefined' ;;
  *) exit 2 ;;
esac
mkdir -p "$destino"
trabalho=$(mktemp -d "${TMPDIR:-/tmp}/santafe-dados2.XXXXXX")
trap 'printf "Construção preservada: %s\n" "$trabalho"' EXIT
cp "$base"/src/*.c "$base"/src/*.h "$base/src/Makefile" "$trabalho/"
cp "$base/ferramentas/sls/nativo.c" "$trabalho/sls_nativo.c"
make -C "$trabalho" -j2 generic MYCFLAGS="$opcoes" MYLDFLAGS="$ligacao" MYOBJS=sls_nativo.o
if [ "${1:-normal}" != estavel ]; then
  cc $opcoes -I"$trabalho" "$base/experimentos/dados-v1/testar-api.c" "$trabalho/liblua.a" -lm $ligacao -o "$trabalho/testar-api"
  "$trabalho/testar-api"
fi
cp "$trabalho/santafé" "$destino/santafé-dados"
cp "$trabalho/santafec" "$destino/santafec-dados"
"$destino/santafé-dados" -E -P -v
