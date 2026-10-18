#!/usr/bin/env bash

set -Eeuo pipefail

ARQUIVO_AMBIENTE=${CORREIO_ARQUIVO_AMBIENTE:-/etc/santafe/correio.env}

if [[ ! -r "$ARQUIVO_AMBIENTE" ]]; then
    echo "ERRO: não foi possível ler $ARQUIVO_AMBIENTE" >&2
    exit 1
fi

BANCO=$(sed -n 's/^SANTAFE_MARIADB_BANCO=//p' "$ARQUIVO_AMBIENTE" | tail -n 1)
BANCO=${BANCO%\"}
BANCO=${BANCO#\"}
BANCO=${BANCO%\'}
BANCO=${BANCO#\'}

if [[ -z "$BANCO" ]]; then
    echo "ERRO: SANTAFE_MARIADB_BANCO não foi definido" >&2
    exit 1
fi

echo "== Estado dos transportes =="
systemctl is-active correio-recebedor.service correio-envios.timer || true
systemctl is-enabled correio-recebedor.service correio-envios.timer || true

echo
echo "== Portas SMTP locais =="
ss -ltn | awk 'NR == 1 || /:(25|2525|465|587)[[:space:]]/'

echo
echo "== Resumo da fila =="
mariadb --batch --raw "$BANCO" <<'SQL'
SELECT estado, COUNT(*) AS quantidade
FROM correio_fila
GROUP BY estado
ORDER BY estado;
SQL

echo
echo "== Últimas vinte entradas da fila (sem conteúdo) =="
mariadb --batch --raw "$BANCO" <<'SQL'
SELECT id, direcao, estado, remetente, destinatarios, tentativas,
       FROM_UNIXTIME(criada_em) AS criada_em, ultima_falha
FROM correio_fila
ORDER BY id DESC
LIMIT 20;
SQL

echo
echo "== Últimas vinte cartas (sem corpo nem anexos) =="
mariadb --batch --raw "$BANCO" <<'SQL'
SELECT id, direcao, pasta, remetente, destinatarios, assunto,
       estado_entrega, falha_entrega, referencia_fila,
       FROM_UNIXTIME(criada_em) AS criada_em
FROM correio_cartas
ORDER BY id DESC
LIMIT 20;
SQL

echo
echo "== DNS postal público =="
printf 'A do domínio: '
dig +short A xn--santaf-gva.dev.br | paste -sd ',' -
printf 'MX do domínio: '
dig +short MX xn--santaf-gva.dev.br | paste -sd ',' -
printf 'A de mail: '
dig +short A mail.xn--santaf-gva.dev.br | paste -sd ',' -
printf 'PTR do servidor: '
dig +short -x 143.208.252.1 | paste -sd ',' -
