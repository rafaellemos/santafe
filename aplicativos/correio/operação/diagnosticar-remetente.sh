#!/usr/bin/env bash

set -Eeuo pipefail

REMETENTE=${1:-juliana@embratel.com.br}
AMBIENTE=/etc/santafe/correio.env

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
    echo "ERRO: execute com sudo para ler apenas os metadados protegidos." >&2
    exit 1
fi
[[ -r "$AMBIENTE" ]] || { echo "ERRO: $AMBIENTE não pode ser lido." >&2; exit 1; }

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

echo "==> Triagem configurada"
grep -E '^CORREIO_TRIAGEM_(ATIVA|LIMITE_)=' "$AMBIENTE" || true

echo "==> Última carta desse remetente"
consulta -e "SELECT id,remetente,assunto,FROM_UNIXTIME(criada_em),pasta,classificacao_triagem,pontuacao_suspeita,motivos_triagem FROM correio_cartas WHERE direcao='entrada' AND LOWER(remetente)=LOWER('$(printf '%s' "$REMETENTE" | sed "s/'/''/g")') ORDER BY id DESC LIMIT 1;"

linha=$(consulta --skip-column-names -e "SELECT id,mime_objeto,tamanho FROM correio_cartas WHERE direcao='entrada' AND LOWER(remetente)=LOWER('$(printf '%s' "$REMETENTE" | sed "s/'/''/g")') ORDER BY id DESC LIMIT 1;")
[[ -n "$linha" ]] || { echo "ERRO: carta não encontrada." >&2; exit 1; }
IFS=$'\t' read -r ID RESUMO TAMANHO <<< "$linha"
[[ "$RESUMO" =~ ^[0-9a-f]{64}$ ]] || {
    echo "ERRO: a carta $ID não possui referência válida no depósito." >&2
    exit 1
}

RAIZ=${CORREIO_DEPOSITO:-/var/lib/santafé/correio}
OBJETO="$RAIZ/objetos/${RESUMO:0:2}/${RESUMO:2:2}/$RESUMO"
[[ -r "$OBJETO" ]] || { echo "ERRO: objeto MIME protegido não encontrado." >&2; exit 1; }

echo "==> Cabeçalhos técnicos armazenados (corpo omitido)"
perl -0777 -ne '
  ($h) = split(/\r?\n\r?\n/, $_, 2);
  $h =~ s/\r?\n[ \t]+/ /g;
  for $l (split(/\r?\n/, $h)) {
    print "$l\n" if $l =~ /^(Received|Return-Path|From|Sender|Reply-To|Date|Message-ID|DKIM-Signature|Authentication-Results|Received-SPF|ARC-Authentication-Results):/i;
  }
' "$OBJETO"

echo "==> Eventos PULSO relacionados (conteúdo e anexos omitidos)"
if [[ -r /var/log/santafé/correio.pulso ]]; then
    grep -F "$REMETENTE" /var/log/santafé/correio.pulso | tail -n 10 || true
else
    echo "PULSO não está legível ou ainda não persistiu eventos."
fi

echo "==> Carta $ID; objeto $RESUMO; tamanho $TAMANHO tacos"
