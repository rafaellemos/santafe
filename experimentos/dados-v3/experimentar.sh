#!/bin/sh
# Iniciador de laboratório. Não instala nem altera o PATH do usuário.
set -eu
base=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
test -f "$base/.laboratorio-dados3" || { echo 'Use a árvore isolada dados.3.' >&2; exit 1; }
test -x "$base/src/santafé" || { echo 'Compile primeiro com sh experimentos/dados-v3/construir.sh.' >&2; exit 1; }
cd "$base"
case "${1:-exemplo}" in
  exemplo) exec ./src/santafé -E -P experimentos/dados-v1/exemplo.fé ;;
  testes)
    ./src/santafé -E -P experimentos/dados-v1/testar.fé
    ./src/santafé -E -P experimentos/dados-v1/testar-onfe.fé
    exec ./src/santafé -E -P experimentos/dados-v3/testar-fronteiras.fé ;;
  sls) exec /bin/sh experimentos/dados-v3/santafe-sls-dados ;;
  *) echo 'Uso: experimentar.sh [exemplo|testes|sls]' >&2; exit 2 ;;
esac
