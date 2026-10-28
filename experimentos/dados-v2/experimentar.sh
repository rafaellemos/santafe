#!/bin/sh
# Somente o pacote local; não instala, não carrega módulos C da produção.
set -eu
base=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$base"
export SANTAFE_CANDIDATO="$base/dist/candidato-dados-v2/santafé-dados"
export SANTAFE_ESTAVEL="$base/dist/candidato-dados-v2-baseline/santafé-dados"
if [ ! -x "$SANTAFE_CANDIDATO" ]; then
  printf 'Primeiro compile: sh experimentos/dados-v2/construir.sh\n' >&2; exit 1
fi
case "${1:-exemplo}" in
  exemplo) exec "$SANTAFE_CANDIDATO" -E -P experimentos/dados-v2/visual.fé ;;
  testar)
    python3 experimentos/dados-v1/testar.py
    python3 experimentos/dados-v2/testar-sls.py
    exec python3 testes/integracao/testar_sls_aceitacao.py --perfil 1.0 --comando /bin/sh "$base/experimentos/dados-v2/santafe-sls-dados" ;;
  sls) exec /bin/sh "$base/experimentos/dados-v2/santafe-sls-dados" ;;
  *) exec "$SANTAFE_CANDIDATO" -E -P -e 'módulo.caminho="experimentos/dados-v1/?.fé"' "$@" ;;
esac
