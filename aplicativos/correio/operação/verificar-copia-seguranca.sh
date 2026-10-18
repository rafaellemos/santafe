#!/usr/bin/env bash

set -euo pipefail

COPIA="${1:-}"
[[ -n "$COPIA" && -d "$COPIA" ]] || {
    echo "Uso: $0 DIRETORIO_DA_COPIA" >&2
    exit 2
}

for arquivo in banco.sql deposito.tar manifesto.txt SHA256SUMS; do
    [[ -f "$COPIA/$arquivo" ]] || {
        echo "ERRO: ausente: $COPIA/$arquivo" >&2
        exit 1
    }
done

(
    cd "$COPIA"
    if command -v sha256sum >/dev/null; then
        sha256sum -c SHA256SUMS
    else
        shasum -a 256 -c SHA256SUMS
    fi
)

grep -Fq 'formato=santafe-correio-copia-1' "$COPIA/manifesto.txt"
grep -Fq 'correio_migracoes' "$COPIA/banco.sql"
tar -tf "$COPIA/deposito.tar" | awk '
    /^\// || /(^|\/)\.\.($|\/)/ { ruim=1 }
    END { exit ruim ? 1 : 0 }
'

echo "Cópia postal íntegra: $COPIA"
