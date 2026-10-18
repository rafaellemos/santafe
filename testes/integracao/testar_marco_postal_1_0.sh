#!/usr/bin/env bash

set -euo pipefail

RAIZ="$(cd "$(dirname "$0")/../.." && pwd)"
MANUAL="${MANUAL_SANTAFE:-$RAIZ/../../SantaFe/1.0/site-sfdev/manual.html}"
VALIDADOR="${VALIDADOR_MANUAL_SANTAFE:-$RAIZ/../../SantaFe/1.0/site-sfdev/validar-manual.py}"
cd "$RAIZ"

echo "==> Conferindo o contrato do marco postal 1.0"
grep -Fq 'versão = "1.0.0"' bibs/bibf/correio.fé
grep -Fq 'versão = "1.0.0"' bibs/bibf/correio/imap.fé
grep -Fq 'versão = "1.0.0"' bibs/bibf/carteiro.fé
for programa in aplicativos/correio/operação/copiar-seguranca.sh \
                aplicativos/correio/operação/verificar-copia-seguranca.sh \
                aplicativos/correio/operação/restaurar-copia-seguranca.sh; do
    bash -n "$programa"
done

echo "==> Executando a suíte geral"
./testar.sh

echo "==> Executando persistência, interrupção e restauração"
./testes/integracao/testar_correio_mariadb.sh

echo "==> Validando o manual"
python3 "$VALIDADOR" "$MANUAL" --compilador "$RAIZ/src/santafec"

echo "✅ Marco Correio/Carteiro 1.0 validado."
