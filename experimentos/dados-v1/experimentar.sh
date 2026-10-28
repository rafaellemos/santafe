#!/bin/sh
set -eu
base=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$base"
binario="$base/dist/candidato-dados-v1/santafé-dados"
if [ ! -x "$binario" ]; then
  printf 'Compile primeiro: sh "%s/experimentos/dados-v1/construir.sh"\n' "$base" >&2
  exit 1
fi
case "${1:-exemplo}" in
  exemplo) exec "$binario" -E -P experimentos/dados-v1/exemplo.fé ;;
  testar) exec python3 experimentos/dados-v1/testar.py ;;
  *) exec "$binario" -E -P -e 'módulo.caminho="experimentos/dados-v1/?.fé"' "$@" ;;
esac
