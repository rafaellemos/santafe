#!/bin/sh
# Candidato isolado. Não instala, não usa sudo e não altera src/*.o.
set -eu
base=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
destino="$base/dist/candidato-dados-v1"
opcoes='-DSANTAFE_DADOS_EXPERIMENTAL -DLUA_USE_APICHECK'
ligacao=''
case "${1:-normal}" in
  normal) ;;
  sanitizado)
    destino="$base/dist/candidato-dados-v1-sanitizado"
    opcoes="$opcoes -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer"
    ligacao='-fsanitize=address,undefined' ;;
  estavel)
    destino="$base/dist/candidato-dados-v1-baseline"
    opcoes='-DLUA_USE_APICHECK' ;;
  *) printf 'Use normal, sanitizado ou estavel.\n' >&2; exit 2 ;;
esac
mkdir -p "$destino"
trabalho=$(mktemp -d "${TMPDIR:-/tmp}/santafe-dados.XXXXXX")
trap 'printf "Fontes e evidências da construção: %s\n" "$trabalho"' EXIT
cp "$base"/src/*.c "$base"/src/*.h "$base/src/Makefile" "$trabalho/"
make -C "$trabalho" -j2 generic MYCFLAGS="$opcoes" MYLDFLAGS="$ligacao"
if [ "${1:-normal}" != estavel ]; then
  # Separação intencional das opções estáticas controladas por este script.
  cc $opcoes -I"$trabalho" "$base/experimentos/dados-v1/testar-api.c" \
    "$trabalho/liblua.a" -lm $ligacao -o "$trabalho/testar-api"
  "$trabalho/testar-api"
fi
cp "$trabalho/santafé" "$destino/santafé-dados"
cp "$trabalho/santafec" "$destino/santafec-dados"
"$destino/santafé-dados" -E -P -v
printf '\nTeste: "%s" -E -P "%s"\n' "$destino/santafé-dados" "$base/experimentos/dados-v1/testar.fé"
