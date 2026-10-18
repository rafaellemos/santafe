#!/usr/bin/env bash

set -Eeuo pipefail

RAIZ="$(cd "$(dirname "$0")/../.." && pwd)"
INTERPRETADOR="${SANTAFE_INTERPRETADOR:-$RAIZ/src/santafé}"
MANUAL="${SANTAFE_MANUAL:-$RAIZ/docs/manual.html}"
WASM="${SANTAFE_WASM:-$RAIZ/src/santafe.wasm}"

if [[ ! -f "$MANUAL" && -f "$RAIZ/../../SantaFe/1.0/site-sfdev/manual.html" ]]; then
    MANUAL="$RAIZ/../../SantaFe/1.0/site-sfdev/manual.html"
fi

[[ -x "$INTERPRETADOR" ]] || {
    echo "Interpretador ausente: $INTERPRETADOR" >&2
    exit 1
}

resultado="$($INTERPRETADOR -e \
    'mostre(tipo(verdadeiro)); mostre(tipo(falso)); mostre(_AMBIENTE ~= nulo)')"
esperado=$'lógico\nlógico\nverdadeiro'
[[ "$resultado" == "$esperado" ]] || {
    echo "Vocabulário inesperado no interpretador:" >&2
    printf '%s\n' "$resultado" >&2
    exit 1
}

if grep -RInF '"booleano"' \
    "$RAIZ/bibs/bibf" "$RAIZ/aplicativos" "$RAIZ/exemplos"; then
    echo 'Um fonte público ainda compara ou publica o tipo "booleano".' >&2
    exit 1
fi

if [[ -f "$MANUAL" ]]; then
    grep -Fq '<code>lógico</code>' "$MANUAL"
    grep -Fq '<code>_AMBIENTE</code>' "$MANUAL"
    if grep -Eq '<td>booleano</td>|<code>booleano</code>' "$MANUAL"; then
        echo 'O manual ainda apresenta booleano como tipo Santafé.' >&2
        exit 1
    fi
fi

if [[ -f "$WASM" ]]; then
    LC_ALL=C grep -aFq 'lógico' "$WASM"
    LC_ALL=C grep -aFq '_AMBIENTE' "$WASM"
    if LC_ALL=C grep -aEq 'booleano|_ENV' "$WASM"; then
        echo 'O executor WebAssembly ainda contém o vocabulário anterior.' >&2
        exit 1
    fi
fi

echo 'Vocabulário público: lógico e _AMBIENTE ok'
