#!/usr/bin/env bash

set -euo pipefail

RAIZ="$(cd "$(dirname "$0")" && pwd)"
cd "$RAIZ"

INTERPRETADOR="./src/santafé"
COMPILADOR="./src/santafec"

if [[ ! -x "$INTERPRETADOR" || ! -x "$COMPILADOR" ]]; then
    echo "ERRO: compile o núcleo primeiro com 'make cbin'." >&2
    exit 1
fi

for biblioteca in rede mariadb segredo tomada; do
    if [[ ! -f "bibs/bibc/$biblioteca/$biblioteca.so" ]]; then
        echo "ERRO: falta bibs/bibc/$biblioteca/$biblioteca.so; rode 'make cbibc'." >&2
        exit 1
    fi
done

export LUA_PATH='bibs/bibf/?.fé;bibs/bibf/?.fe;;'
export LUA_CPATH='bibs/bibc/?/?.so;;'

echo "==> Conferindo a sintaxe dos fontes Santafé"
while IFS= read -r -d '' arquivo; do
    "$COMPILADOR" -p "$arquivo"
done < <(find exemplos testes bibs/bibf -type f \( -name '*.fé' -o -name '*.fé' \) -print0)

echo "==> Executando exemplos"
for arquivo in exemplos/*.fé; do
    "$INTERPRETADOR" "$arquivo" >/dev/null
done

testes=(testes/metatabelas.fé)
while IFS= read -r -d '' arquivo; do
    testes+=("$arquivo")
done < <(find testes/bibc testes/bibf -type f -name 'teste_*.f*' -print0)

echo "==> Executando testes"
for arquivo in "${testes[@]}"; do
    printf '    %s\n' "$arquivo"
    "$INTERPRETADOR" "$arquivo"
done

echo "✅ Todos os testes disponíveis passaram."
echo "   Os testes MariaDB são ignorados sem as variáveis SANTAFE_MARIADB_*."
