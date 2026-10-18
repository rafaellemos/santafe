#!/usr/bin/env bash

set -euo pipefail
umask 077

AMBIENTE="${CORREIO_AMBIENTE:-/etc/santafe/correio.env}"
DESTINO_BASE="${CORREIO_COPIAS:-/var/backups/santafe-correio}"

falhe() {
    echo "ERRO: $*" >&2
    exit 1
}

[[ -r "$AMBIENTE" ]] || falhe "não foi possível ler $AMBIENTE"
set -a
# O arquivo pertence ao administrador e contém apenas a configuração do
# serviço. Segredos nunca são impressos nem copiados para o manifesto.
source "$AMBIENTE"
set +a

: "${SANTAFE_MARIADB_HOST:?SANTAFE_MARIADB_HOST ausente}"
: "${SANTAFE_MARIADB_PORTA:?SANTAFE_MARIADB_PORTA ausente}"
: "${SANTAFE_MARIADB_USUARIO:?SANTAFE_MARIADB_USUARIO ausente}"
: "${SANTAFE_MARIADB_SENHA:?SANTAFE_MARIADB_SENHA ausente}"
: "${SANTAFE_MARIADB_BANCO:?SANTAFE_MARIADB_BANCO ausente}"
: "${CORREIO_DEPOSITO:?CORREIO_DEPOSITO ausente}"

command -v mariadb >/dev/null || falhe "mariadb não encontrado"
command -v mariadb-dump >/dev/null || falhe "mariadb-dump não encontrado"
[[ -d "$CORREIO_DEPOSITO" ]] || falhe "Depósito inexistente: $CORREIO_DEPOSITO"

autenticacao=(--host="$SANTAFE_MARIADB_HOST" --port="$SANTAFE_MARIADB_PORTA"
    --user="$SANTAFE_MARIADB_USUARIO" --protocol=tcp)
export MYSQL_PWD="$SANTAFE_MARIADB_SENHA"
if [[ "$(id -u)" -eq 0 ]] &&
   mariadb --protocol=socket --user=root -N -e 'SELECT 1' >/dev/null 2>&1; then
    autenticacao=(--protocol=socket --user=root)
    unset MYSQL_PWD
fi

carimbo="$(date +%Y%m%d-%H%M%S)"
destino="$DESTINO_BASE/$carimbo"
temporario="$DESTINO_BASE/.${carimbo}.parcial"
[[ ! -e "$destino" && ! -e "$temporario" ]] || falhe "destino já existe"
mkdir -p "$temporario"

encerre() {
    local codigo=$?
    if [[ "$codigo" -ne 0 ]]; then
        rm -rf -- "$temporario"
    fi
    return "$codigo"
}
trap encerre EXIT INT TERM

echo "==> Copiando o banco compartilhado de forma transacional"
# O banco inclui a identidade usada pelo Correio. A cópia fica privada porque
# contém resumos de senha, embora nunca contenha senhas em texto puro.
mariadb-dump "${autenticacao[@]}" \
    --single-transaction --quick --routines --events --triggers \
    --hex-blob --default-character-set=utf8mb4 --skip-comments \
    --order-by-primary "$SANTAFE_MARIADB_BANCO" > "$temporario/banco.sql"
[[ -s "$temporario/banco.sql" ]] || falhe "cópia SQL ficou vazia"
grep -Fq 'correio_migracoes' "$temporario/banco.sql" ||
    falhe "cópia SQL não contém a estrutura postal"

echo "==> Copiando o Depósito imutável"
# O banco vem primeiro: todo objeto que ele referencia já existe. Objetos
# criados durante o tar podem sobrar na cópia, mas nunca faltarão ao banco.
tar -cf "$temporario/deposito.tar" -C "$CORREIO_DEPOSITO" .
tar -tf "$temporario/deposito.tar" >/dev/null

cat > "$temporario/manifesto.txt" <<EOF
formato=santafe-correio-copia-1
criada_em=$(date --iso-8601=seconds 2>/dev/null || date '+%Y-%m-%dT%H:%M:%S%z')
banco=$SANTAFE_MARIADB_BANCO
deposito=$CORREIO_DEPOSITO
metodo_banco=transacao-unica
ordem=banco-depois-deposito
EOF

(
    cd "$temporario"
    if command -v sha256sum >/dev/null; then
        sha256sum banco.sql deposito.tar manifesto.txt > SHA256SUMS
    else
        shasum -a 256 banco.sql deposito.tar manifesto.txt > SHA256SUMS
    fi
)

mv "$temporario" "$destino"
trap - EXIT INT TERM
unset MYSQL_PWD 2>/dev/null || true
echo "Cópia postal concluída: $destino"
echo "Valide com: /opt/correio/operação/verificar-copia-seguranca.sh '$destino'"
