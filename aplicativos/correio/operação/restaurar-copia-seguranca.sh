#!/usr/bin/env bash

set -euo pipefail
umask 077

COPIA="${1:-}"
BANCO_DESTINO="${2:-}"
DEPOSITO_DESTINO="${3:-}"
AMBIENTE="${CORREIO_AMBIENTE:-/etc/santafe/correio.env}"

uso() {
    echo "Uso: $0 COPIA BANCO_NOVO DEPOSITO_NOVO" >&2
    echo "A restauração nunca substitui a produção; cria destinos novos." >&2
    exit 2
}

[[ -n "$COPIA" && -n "$BANCO_DESTINO" && -n "$DEPOSITO_DESTINO" ]] || uso
[[ "$BANCO_DESTINO" =~ ^[A-Za-z0-9_]+$ ]] || {
    echo "ERRO: nome do banco de destino inválido" >&2
    exit 1
}
[[ -r "$AMBIENTE" ]] || { echo "ERRO: não foi possível ler $AMBIENTE" >&2; exit 1; }

"$(dirname "$0")/verificar-copia-seguranca.sh" "$COPIA"

set -a
source "$AMBIENTE"
set +a
: "${SANTAFE_MARIADB_HOST:?SANTAFE_MARIADB_HOST ausente}"
: "${SANTAFE_MARIADB_PORTA:?SANTAFE_MARIADB_PORTA ausente}"
: "${SANTAFE_MARIADB_USUARIO:?SANTAFE_MARIADB_USUARIO ausente}"
: "${SANTAFE_MARIADB_SENHA:?SANTAFE_MARIADB_SENHA ausente}"

command -v mariadb >/dev/null || { echo "ERRO: mariadb não encontrado" >&2; exit 1; }
[[ ! -e "$DEPOSITO_DESTINO" ]] || {
    echo "ERRO: o Depósito de destino já existe: $DEPOSITO_DESTINO" >&2
    exit 1
}

cliente=(mariadb --host="$SANTAFE_MARIADB_HOST"
    --port="$SANTAFE_MARIADB_PORTA" --user="$SANTAFE_MARIADB_USUARIO"
    --protocol=tcp --default-character-set=utf8mb4)
export MYSQL_PWD="$SANTAFE_MARIADB_SENHA"
if [[ "$(id -u)" -eq 0 ]] &&
   mariadb --protocol=socket --user=root -N -e 'SELECT 1' >/dev/null 2>&1; then
    cliente=(mariadb --protocol=socket --user=root
        --default-character-set=utf8mb4)
    unset MYSQL_PWD
fi
existe="$("${cliente[@]}" -N -e \
    "SELECT COUNT(*) FROM information_schema.SCHEMATA WHERE SCHEMA_NAME='$BANCO_DESTINO'")"
[[ "$existe" == 0 ]] || {
    echo "ERRO: o banco de destino já existe: $BANCO_DESTINO" >&2
    exit 1
}

criou_banco=falso
criou_deposito=falso
encerre() {
    local codigo=$?
    if [[ "$codigo" -ne 0 ]]; then
        [[ "$criou_banco" == verdadeiro ]] &&
            "${cliente[@]}" -e \
                "DROP DATABASE IF EXISTS \`$BANCO_DESTINO\`" || true
        [[ "$criou_deposito" == verdadeiro ]] && rm -rf -- "$DEPOSITO_DESTINO"
    fi
    return "$codigo"
}
trap encerre EXIT INT TERM

echo "==> Restaurando o banco em $BANCO_DESTINO"
"${cliente[@]}" -e \
    "CREATE DATABASE \`$BANCO_DESTINO\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
criou_banco=verdadeiro
"${cliente[@]}" "$BANCO_DESTINO" < \
    "$COPIA/banco.sql"

echo "==> Restaurando o Depósito em $DEPOSITO_DESTINO"
mkdir -p "$DEPOSITO_DESTINO"
criou_deposito=verdadeiro
tar -xf "$COPIA/deposito.tar" -C "$DEPOSITO_DESTINO"

migracoes="$("${cliente[@]}" -N \
    "$BANCO_DESTINO" -e \
    "SELECT COUNT(*) FROM correio_migracoes WHERE componente='correio' AND versao BETWEEN 1 AND 9")"
[[ "$migracoes" == 9 ]] || {
    echo "ERRO: restauração não possui as nove migrações postais" >&2
    exit 1
}

trap - EXIT INT TERM
unset MYSQL_PWD 2>/dev/null || true
echo "Restauração de ensaio concluída. A produção não foi alterada."
echo "Banco: $BANCO_DESTINO"
echo "Depósito: $DEPOSITO_DESTINO"
