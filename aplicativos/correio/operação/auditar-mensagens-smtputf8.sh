#!/usr/bin/env bash

set -Eeuo pipefail

AMBIENTE=${CORREIO_ARQUIVO_AMBIENTE:-/etc/santafe/correio.env}
LIMITE=${1:-16}

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
    echo "ERRO: execute com sudo para ler as cartas protegidas." >&2
    exit 1
fi
[[ "$LIMITE" =~ ^[0-9]+$ ]] && (( LIMITE >= 1 && LIMITE <= 50 )) || {
    echo "ERRO: o limite precisa ser um inteiro entre 1 e 50." >&2
    exit 1
}
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

RAIZ=${CORREIO_DEPOSITO:-/var/lib/santafé/correio}

echo "==> Serviços postais"
systemctl is-active correio-recebedor.service correio-agencia.service \
    correio-imap.service carteiro.service correio-envios.timer || true

echo "==> Identidades e caixas"
consulta -e "
SELECT u.id,u.usuario,HEX(u.usuario) AS usuario_hex,u.email,
       HEX(u.email) AS email_hex,c.id AS caixa_id,c.parte_local,
       HEX(c.parte_local) AS parte_local_hex,c.dominio_ascii,
       c.endereco_exibido,HEX(c.endereco_exibido) AS endereco_hex
FROM usuarios u
LEFT JOIN correio_caixas c ON c.usuario_id=u.id
ORDER BY u.id DESC LIMIT 30;"

echo "==> Fila de transporte recente"
consulta -e "
SELECT id,direcao,estado,remetente,HEX(remetente) AS remetente_hex,
       destinatarios,HEX(destinatarios) AS destinatarios_hex,tentativas,
       FROM_UNIXTIME(criada_em) AS criada_em,ultima_falha
FROM correio_fila ORDER BY id DESC LIMIT 30;"

mapfile -t CARTAS < <(consulta --skip-column-names -e \
    "SELECT id FROM correio_cartas ORDER BY id DESC LIMIT ${LIMITE};")

echo "==> ${#CARTAS[@]} cartas recentes: metadados, corpo e MIME"
for carta in "${CARTAS[@]}"; do
    [[ "$carta" =~ ^[0-9]+$ ]] || continue
    echo
    echo "================================================================"
    echo "CARTA $carta"
    echo "================================================================"
    consulta -e "
SELECT id,caixa_id,uid_imap,direcao,pasta,identificacao,
       remetente,HEX(remetente) AS remetente_hex,
       destinatarios,HEX(destinatarios) AS destinatarios_hex,
       assunto,HEX(assunto) AS assunto_hex,responder_para,
       estado_entrega,falha_entrega,referencia_fila,
       resultado_spf,resultado_dkim,resultado_dmarc,dominio_autor,
       classificacao_triagem,pontuacao_suspeita,
       FROM_UNIXTIME(criada_em) AS criada_em,mime_objeto,tamanho,
       CASE WHEN CHAR_LENGTH(texto)>20000
            THEN CONCAT(LEFT(texto,20000),'\n...[texto cortado em 20000 caracteres]')
            ELSE texto END AS corpo_texto,
       CASE WHEN CHAR_LENGTH(html)>20000
            THEN CONCAT(LEFT(html,20000),'\n...[HTML cortado em 20000 caracteres]')
            ELSE html END AS corpo_html
FROM correio_cartas WHERE id=${carta}\\G"

    echo "-- anexos (conteúdo binário omitido) --"
    consulta -e "
SELECT id,nome,HEX(nome) AS nome_hex,tipo,tamanho,dados_objeto
FROM correio_anexos WHERE carta_id=${carta} ORDER BY id;"

    resumo=$(consulta --skip-column-names -e \
        "SELECT COALESCE(mime_objeto,'') FROM correio_cartas WHERE id=${carta};")
    if [[ "$resumo" =~ ^[0-9a-f]{64}$ ]]; then
        objeto="$RAIZ/objetos/${resumo:0:2}/${resumo:2:2}/$resumo"
        echo "-- cabeçalhos MIME brutos do objeto $resumo --"
        if [[ -r "$objeto" ]]; then
            perl -0777 -ne '($h) = split(/\r?\n\r?\n/, $_, 2); print $h, "\n"' \
                "$objeto"
        else
            echo "OBJETO INACESSÍVEL: $objeto"
        fi
    else
        echo "-- carta sem objeto MIME externo --"
    fi
done

echo
echo "==> PULSO postal recente"
if [[ -r /var/log/santafé/correio.pulso ]]; then
    tail -n 5000 /var/log/santafé/correio.pulso | \
        grep -aE 'correio\.(agência|imap|entrega|mensagem|cd\.|autenticação)' | \
        tail -n 400 || true
else
    echo "PULSO não está legível."
fi

echo "Auditoria concluída: corpos textuais incluídos; tacos dos anexos omitidos."
