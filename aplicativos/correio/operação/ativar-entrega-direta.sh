#!/usr/bin/env bash

set -Eeuo pipefail

DOMINIO=xn--santaf-gva.dev.br
IP=143.208.252.1
SELETOR=sf2026
CHAVE=/etc/santafe-correio/dkim/sf2026.pem
ARQUIVO_AMBIENTE=/etc/santafe/correio.env
ZONA_REVERSA=252.208.143.in-addr.arpa.
DS_ESPERADO='19001 8 2 2DFCC05CA11293607CE671FE6407A934998AB73F66044222E6E6AB34C7393C97'
RESOLVEDORES=(1.1.1.1 8.8.8.8)

[[ "$EUID" -eq 0 ]] || {
    echo "Execute com sudo." >&2
    exit 1
}

falhe() {
    echo "ERRO: $*" >&2
    exit 1
}

normalize_txt() {
    tr -d '"\n '
}

[[ -r "$CHAVE" ]] || falhe "chave DKIM ausente ou ilegível: $CHAVE"
[[ -r "$ARQUIVO_AMBIENTE" ]] ||
    falhe "ambiente do Correio ausente ou ilegível: $ARQUIVO_AMBIENTE"

BANCO="$(sed -n 's/^SANTAFE_MARIADB_BANCO=//p' "$ARQUIVO_AMBIENTE" |
    tail -n 1)"
BANCO="${BANCO#\"}"; BANCO="${BANCO%\"}"
BANCO="${BANCO#\'}"; BANCO="${BANCO%\'}"
[[ -n "$BANCO" ]] || falhe "SANTAFE_MARIADB_BANCO não foi definido"

PUBLICA="$(openssl pkey -in "$CHAVE" -pubout -outform DER 2>/dev/null |
    base64 -w0)"

para_resolvedor() {
    local resolvedor=$1
    local mx spf dkim dmarc ptr ds resposta_ptr

    echo "==> Validando a identidade postal em $resolvedor"

    mx="$(dig +short @"$resolvedor" MX "$DOMINIO")"
    spf="$(dig +short @"$resolvedor" TXT "$DOMINIO" | normalize_txt)"
    dkim="$(dig +short @"$resolvedor" TXT \
        "$SELETOR._domainkey.$DOMINIO" | normalize_txt)"
    dmarc="$(dig +short @"$resolvedor" TXT \
        "_dmarc.$DOMINIO" | normalize_txt)"
    ptr="$(dig +short @"$resolvedor" -x "$IP" | head -n1)"
    ds="$(dig +short @"$resolvedor" DS "$ZONA_REVERSA" | awk '
        NF >= 4 {
            resumo = $4
            for (i = 5; i <= NF; i++) resumo = resumo $i
            print $1, $2, $3, toupper(resumo)
            exit
        }')"
    resposta_ptr="$(dig @"$resolvedor" -x "$IP" +dnssec +noall +comments)"

    [[ "$mx" == *"$DOMINIO."* ]] ||
        falhe "MX ainda ausente em $resolvedor"
    [[ "$spf" == *"v=spf1"* && "$spf" == *"ip4:$IP"* ]] ||
        falhe "SPF ainda ausente ou divergente em $resolvedor"
    [[ "$dkim" == *"p=$PUBLICA"* ]] ||
        falhe "DKIM ainda ausente ou divergente em $resolvedor"
    [[ "$dmarc" == *"v=DMARC1"* ]] ||
        falhe "DMARC ainda ausente em $resolvedor"
    [[ "$ptr" == "$DOMINIO." ]] ||
        falhe "PTR ainda ausente ou divergente em $resolvedor: ${ptr:-vazio}"
    [[ "$ds" == "$DS_ESPERADO" ]] ||
        falhe "DS reverso ainda não propagou em $resolvedor"
    grep -Eq 'flags:.*(^|[[:space:]])ad([;[:space:]]|$)' <<<"$resposta_ptr" ||
        falhe "PTR ainda não foi validado por DNSSEC em $resolvedor"
}

for resolvedor in "${RESOLVEDORES[@]}"; do
    para_resolvedor "$resolvedor"
done

echo "==> Validando o certificado SMTP"
resultado_tls="$(timeout 15 openssl s_client -starttls smtp -connect 127.0.0.1:25 \
    -servername "$DOMINIO" -verify_hostname "$DOMINIO" -brief \
    </dev/null 2>&1)" ||
    falhe "não foi possível negociar STARTTLS"
grep -q 'Verification: OK' <<<"$resultado_tls" ||
    falhe "o certificado STARTTLS não foi validado"

systemctl is-active --quiet correio-recebedor.service ||
    falhe "correio-recebedor.service não está ativo"
ss -H -ltn | awk '$4 ~ /(^|:)25$/ || $4 ~ /\]:25$/ {ok=1} END {exit !ok}' ||
    falhe "a porta TCP 25 não está escutando"

mostre_fila() {
    local titulo=$1
    echo "==> $titulo"
    mariadb --batch --raw "$BANCO" <<'SQL'
SELECT estado, COUNT(*) AS quantidade
FROM correio_fila
GROUP BY estado
ORDER BY estado;
SELECT id, direcao, estado, remetente, destinatarios, tentativas,
       FROM_UNIXTIME(criada_em) AS criada_em, ultima_falha
FROM correio_fila
ORDER BY id DESC
LIMIT 10;
SQL
}

mostre_fila "Fila antes da ativação"

timer_era_habilitado=falso
if systemctl is-enabled --quiet correio-envios.timer; then
    timer_era_habilitado=verdadeiro
fi

restaure_timer() {
    local estado=$?
    if [[ "$timer_era_habilitado" == falso ]]; then
        systemctl disable --now correio-envios.timer >/dev/null 2>&1 || true
    fi
    exit "$estado"
}

trap restaure_timer ERR
systemctl enable --now correio-envios.timer
systemctl start correio-envios.service
systemctl is-enabled --quiet correio-envios.timer
systemctl is-active --quiet correio-envios.timer
mostre_fila "Fila depois do primeiro processamento"
echo "==> Últimos registros do processador"
journalctl -u correio-envios.service -n 40 --no-pager -l
trap - ERR

echo "Entrega direta ativada. A fila será processada a cada 15 segundos."
