#!/usr/bin/env bash

set -Eeuo pipefail

AMBIENTE=${CORREIO_ARQUIVO_AMBIENTE:-/etc/santafe/correio.env}
ALVO=${1:-josé}
CARTA_ALVO=${2:-}

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
    echo "ERRO: execute com sudo para ler os metadados postais protegidos." >&2
    exit 1
fi
[[ -r "$AMBIENTE" ]] || {
    echo "ERRO: $AMBIENTE não pode ser lido." >&2
    exit 1
}

set -a
# shellcheck disable=SC1090
source "$AMBIENTE"
set +a

: "${SANTAFE_MARIADB_USUARIO:?usuário MariaDB ausente}"
: "${SANTAFE_MARIADB_BANCO:?banco MariaDB ausente}"

consulta() {
    MYSQL_PWD=${SANTAFE_MARIADB_SENHA:-} mariadb --batch --raw \
        --default-character-set=utf8mb4 \
        --host="${SANTAFE_MARIADB_HOST:-127.0.0.1}" \
        --port="${SANTAFE_MARIADB_PORTA:-3306}" \
        --user="$SANTAFE_MARIADB_USUARIO" \
        "$SANTAFE_MARIADB_BANCO" "$@"
}

ALVO_SQL=${ALVO//\'/\'\'}

echo "==> Serviços postais"
systemctl is-active correio-agencia.service correio-recebedor.service \
    correio-envios.timer correio-imap.service || true

echo "==> Identidade e caixa (texto e tacos hexadecimais)"
consulta -e "SELECT u.id,u.usuario,HEX(u.usuario) AS usuario_hex,u.email,HEX(u.email) AS email_hex,c.id AS caixa_id,c.parte_local,HEX(c.parte_local) AS parte_local_hex,c.dominio_ascii,c.endereco_exibido,HEX(c.endereco_exibido) AS endereco_hex FROM usuarios u LEFT JOIN correio_caixas c ON c.usuario_id=u.id WHERE u.usuario LIKE '${ALVO_SQL}%' OR c.parte_local LIKE '${ALVO_SQL}%' ORDER BY u.id DESC LIMIT 10;"

echo "==> Fila relacionada (sem corpo)"
consulta -e "SELECT id,direcao,estado,remetente,HEX(remetente) AS remetente_hex,destinatarios,HEX(destinatarios) AS destinatarios_hex,tentativas,ultima_falha FROM correio_fila WHERE remetente LIKE '${ALVO_SQL}%' OR destinatarios LIKE '%${ALVO_SQL}%' ORDER BY id DESC LIMIT 20;"

echo "==> Cartas relacionadas (sem corpo nem anexos)"
consulta -e "SELECT id,direcao,pasta,remetente,HEX(remetente) AS remetente_hex,destinatarios,HEX(destinatarios) AS destinatarios_hex,assunto,estado_entrega,falha_entrega,mime_objeto FROM correio_cartas WHERE remetente LIKE '${ALVO_SQL}%' OR destinatarios LIKE '%${ALVO_SQL}%' ORDER BY id DESC LIMIT 20;"

echo "==> Cabeçalhos MIME da carta de saída mais recente"
if [[ -n "$CARTA_ALVO" ]]; then
    [[ "$CARTA_ALVO" =~ ^[0-9]+$ ]] || {
        echo "ERRO: a identificação da carta precisa ser numérica." >&2
        exit 1
    }
    linha=$(consulta --skip-column-names -e "SELECT id,mime_objeto FROM correio_cartas WHERE id=${CARTA_ALVO} AND mime_objeto IS NOT NULL LIMIT 1;")
else
    linha=$(consulta --skip-column-names -e "SELECT id,mime_objeto FROM correio_cartas WHERE direcao='saida' AND (remetente LIKE '${ALVO_SQL}%' OR destinatarios LIKE '%${ALVO_SQL}%') AND mime_objeto IS NOT NULL ORDER BY id DESC LIMIT 1;")
fi
if [[ -n "$linha" ]]; then
    IFS=$'\t' read -r CARTA RESUMO <<< "$linha"
    if [[ "$RESUMO" =~ ^[0-9a-f]{64}$ ]]; then
        RAIZ=${CORREIO_DEPOSITO:-/var/lib/santafé/correio}
        OBJETO="$RAIZ/objetos/${RESUMO:0:2}/${RESUMO:2:2}/$RESUMO"
        if [[ -r "$OBJETO" ]]; then
            CABECALHOS=$(mktemp)
            trap 'rm -f -- "${CABECALHOS:-}"' EXIT
            perl -0777 -ne '($h) = split(/\r?\n\r?\n/, $_, 2); print $h' \
                "$OBJETO" > "$CABECALHOS"
            grep -aiE '^(From|To|Cc|Reply-To|Subject|Message-ID|Content-Type|Content-Transfer-Encoding):' \
                "$CABECALHOS" || true
            echo "-- mesmos cabeçalhos em hexadecimal --"
            od -An -tx1 -v "$CABECALHOS"
            echo "Carta: $CARTA; objeto: $RESUMO"
        else
            echo "Objeto MIME não está legível: $OBJETO"
        fi
    fi
else
    echo "Nenhuma carta de saída correspondente foi encontrada."
fi

echo "==> PULSO recente relacionado a SMTPUTF8/entrega"
if [[ -r /var/log/santafé/correio.pulso ]]; then
    tail -n 1200 /var/log/santafé/correio.pulso | \
        grep -aE "${ALVO}|SMTPUTF8|correio\\.(agência|entrega|cd\\.carta|autoriza)" | \
        tail -n 120 || true
else
    echo "PULSO não está legível."
fi

echo "Diagnóstico SMTPUTF8 concluído; nenhum corpo ou anexo foi exibido."
