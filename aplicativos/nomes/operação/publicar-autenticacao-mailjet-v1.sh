#!/usr/bin/env bash
set -euo pipefail

if [[ -e /etc/santafe-nomes/zonas.fé || ! -e /etc/santafe/dns-zonas.fé ]]; then
    SERVICE="nomes-autoridade.service"
    ENV_FILE="/etc/santafe-nomes/nomes.env"
    APPLICATION="/opt/santafe-nomes/autoridade.fé"
    SERVICE_USER="nomes-santafe"
    SERVICE_GROUP="nomes-santafe"
    ZONES_VARIABLE="NOMES_ZONAS_ARQUIVO"
    ADDRESS_VARIABLE="NOMES_AUTORIDADE_ENDERECO"
    PORT_VARIABLE="NOMES_AUTORIDADE_PORTA"
else
    SERVICE="dns-autoritativo.service"
    ENV_FILE="/etc/santafe/dns.env"
    APPLICATION="/opt/santafe-dns/autoritativo.fé"
    SERVICE_USER="dns-santafe"
    SERVICE_GROUP="dns-santafe"
    ZONES_VARIABLE="DNS_ZONAS_ARQUIVO"
    ADDRESS_VARIABLE="DNS_AUTORITATIVO_ENDERECO"
    PORT_VARIABLE="DNS_AUTORITATIVO_PORTA"
fi
DOMAIN="xn--santaf-gva.dev.br."
PRIMARY_ADDRESS="143.208.252.1"
AUTHORITATIVE_ADDRESS=""
PREFLIGHT_ADDRESS="127.0.0.1"
PREFLIGHT_PORT="15354"
PREFLIGHT_UNIT="santafe-preflight-mailjet-auth.service"
NEW_SPF="v=spf1 include:spf.mailjet.com ip4:143.208.252.1 -all"
DKIM_HOST="mailjet._domainkey"
DKIM_PART1="k=rsa; p=MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAo6m7J+h9tDL0ZUqD8SpUJBUSFemOIa4TUPs0HKLODnXaf8leUGiEBVRyvSOvE8corH+4waUmCO8ck1LgiDkoyTue2VoDwVRsmowrvqVzZZH+oVdFctPw6O+T7TqQeSTxqdVIE0ReX1Qk119ondB2d7uqZXjoB+HbCCyPifiQZROTn1zFqpvc8JtmqIi"
DKIM_PART2="ApGDpHaoUKQ3K/bRP2sVVWe+logdYXAsbImanWYTB5+jizp5VCgd8QaTDvfdLIwG8TABYaBRNMPRZqEjVgYdXaxq7UdyHQyXBNjPTPqjCJyC0SD6zQXXUndhcaGKO7+LxS1efn3ljAlGleLuPqRcvwWvFXwIDAQAB"
DKIM_VALUE="${DKIM_PART1}${DKIM_PART2}"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="/var/backups/santafe-mailjet-auth-${STAMP}"
WORK_FILE="$(mktemp /var/tmp/santafe-mailjet-auth.XXXXXX)"
INSTALLED=0
DONE=0
PREFLIGHT_ACTIVE=0

stop_preflight() {
    systemctl stop "$PREFLIGHT_UNIT" >/dev/null 2>&1 || true
    systemctl reset-failed "$PREFLIGHT_UNIT" >/dev/null 2>&1 || true
    PREFLIGHT_ACTIVE=0
}

cleanup() {
    stop_preflight
    rm -f "$WORK_FILE" "${WORK_FILE}.novo"
}

rollback() {
    local code="$?"
    trap - ERR INT TERM
    if [ "$DONE" -eq 1 ]; then
        cleanup
        exit 0
    fi
    printf 'ERRO: autenticação Mailjet interrompida na linha %s (código %s).\n' \
        "${BASH_LINENO[0]:-?}" "$code" >&2
    if [ "$INSTALLED" -eq 1 ] && [ -f "$BACKUP_DIR/zonas.fé" ]; then
        install -o root -g "$SERVICE_GROUP" -m 0640 \
            "$BACKUP_DIR/zonas.fé" "$ZONE_FILE"
        systemctl restart "$SERVICE" || true
        printf 'Zona anterior restaurada. Cópia: %s\n' "$BACKUP_DIR" >&2
    fi
    cleanup
    exit "$code"
}

aguarde_txt() {
    local servidor="$1"
    local porta="$2"
    local nome="$3"
    local esperado="$4"
    local resposta=""
    local compacta=""
    local tentativa
    for ((tentativa = 1; tentativa <= 40; tentativa++)); do
        if resposta="$(dig +time=1 +tries=1 +short \
                @"$servidor" -p "$porta" "$nome" TXT 2>/dev/null)"; then
            compacta="$(tr -d '"[:space:]' <<<"$resposta")"
            if [[ "$compacta" == *"$esperado"* ]]; then
                printf '%s' "$resposta"
                return 0
            fi
        fi
        sleep 0.25
    done
    return 1
}

aguarde_assinatura() {
    local servidor="$1"
    local porta="$2"
    local nome="$3"
    local resposta=""
    local tentativa
    for ((tentativa = 1; tentativa <= 40; tentativa++)); do
        if resposta="$(dig +time=1 +tries=1 \
                @"$servidor" -p "$porta" "$nome" TXT +dnssec \
                2>/dev/null)" &&
                grep -Fq 'RRSIG' <<<"$resposta"; then
            printf '%s' "$resposta"
            return 0
        fi
        sleep 0.25
    done
    return 1
}

trap rollback ERR INT TERM

test "$(id -u)" -eq 0
command -v awk >/dev/null
command -v dig >/dev/null
command -v systemd-run >/dev/null
test "${#DKIM_PART1}" -le 255
test "${#DKIM_PART2}" -le 255
test -r "$ENV_FILE"

ZONE_FILE="$(sed -n "s/^${ZONES_VARIABLE}=//p" "$ENV_FILE" | tail -n 1)"
test -n "$ZONE_FILE"
case "$ZONE_FILE" in
    /*) ;;
    *) printf 'ERRO: NOMES_ZONAS_ARQUIVO não é absoluto.\n' >&2; exit 1 ;;
esac
test -r "$ZONE_FILE"
AUTHORITATIVE_ADDRESS="$(sed -n \
    "s/^${ADDRESS_VARIABLE}=//p" "$ENV_FILE" | tail -n 1)"
[[ "$AUTHORITATIVE_ADDRESS" =~ ^[0-9a-fA-F:.]+$ ]] || {
    printf 'ERRO: endereço da autoridade não foi encontrado no ambiente.\n' >&2
    exit 1
}

mkdir -p "$BACKUP_DIR"
install -m 0600 "$ZONE_FILE" "$BACKUP_DIR/zonas.fé"
cp "$ZONE_FILE" "$WORK_FILE"
compact_spf="$(tr -d '"[:space:]' <<<"$NEW_SPF")"
compact_expected="$(tr -d '"[:space:]' <<<"$DKIM_VALUE")"
base_serial="$(dig +time=2 +tries=2 +short @"$PRIMARY_ADDRESS" \
    "$DOMAIN" SOA 2>/dev/null | awk '{ print $3; exit }')"
[[ "$base_serial" =~ ^[0-9]+$ ]] || {
    printf 'ERRO: não foi possível obter a série da autoridade principal.\n' >&2
    exit 1
}

if ! grep -Fq "$NEW_SPF" "$WORK_FILE" ||
        ! grep -Fq "nome = \"$DKIM_HOST\"" "$WORK_FILE"; then
    dkim_present=0
    grep -Fq "nome = \"$DKIM_HOST\"" "$WORK_FILE" && dkim_present=1
    awk -v domain="$DOMAIN" -v new_spf="$NEW_SPF" \
        -v dkim_host="$DKIM_HOST" -v dkim_part1="$DKIM_PART1" \
        -v dkim_part2="$DKIM_PART2" \
        -v dkim_present="$dkim_present" -v base="$base_serial" '
        BEGIN {
            need_spf = 1
            need_dkim = dkim_present ? 0 : 1
        }
        {
            line = $0
            if (!in_zone && index(line, "nome = \"" domain "\"") > 0) {
                in_zone = 1
                found_domain = 1
            }
            if (in_zone && !serial_done &&
                    match(line, /série[[:space:]]*=[[:space:]]*[0-9]+/)) {
                expression = substr(line, RSTART, RLENGTH)
                old = expression
                sub(/^.*=[[:space:]]*/, "", old)
                old += 0
                fresh = old >= base ? old + 1 : base
                sub(/[0-9]+/, fresh, expression)
                line = substr(line, 1, RSTART - 1) expression \
                    substr(line, RSTART + RLENGTH)
                serial_done = 1
            }

            if (in_zone && need_spf && index(line, "v=spf1") > 0) {
                position = index(line, "v=spf1")
                remainder = substr(line, position)
                quote = index(remainder, "\"")
                if (quote > 0) {
                    line = substr(line, 1, position - 1) new_spf \
                        substr(remainder, quote)
                    need_spf = 0
                }
            }

            print line

            if (in_zone && need_dkim &&
                    line ~ /registros[[:space:]]*=[[:space:]]*\{/) {
                print "            { nome = \"" dkim_host "\", tipo = \"TXT\","
                print "                dados = {"
                print "                    \"" dkim_part1 "\","
                print "                    \"" dkim_part2 "\""
                print "                } },"
                need_dkim = 0
            }
        }
        END {
            if (!found_domain) {
                print "ERRO: zona Santafé não encontrada." > "/dev/stderr"
                exit 42
            }
            if (!serial_done) {
                print "ERRO: série SOA da zona Santafé não encontrada." > "/dev/stderr"
                exit 43
            }
            if (need_spf) {
                print "ERRO: SPF anterior não foi localizado nem atualizado." > "/dev/stderr"
                exit 44
            }
            if (need_dkim) {
                print "ERRO: DKIM Mailjet não foi localizado nem inserido." > "/dev/stderr"
                exit 45
            }
        }
    ' "$WORK_FILE" > "${WORK_FILE}.novo"
    mv "${WORK_FILE}.novo" "$WORK_FILE"

    /usr/local/bin/santafec -p "$WORK_FILE"
    grep -Fq "$NEW_SPF" "$WORK_FILE"
    grep -Fq "$DKIM_PART1" "$WORK_FILE"
    grep -Fq "$DKIM_PART2" "$WORK_FILE"

    echo '==> Testando a zona nova em 127.0.0.1:15354'
    chown root:"$SERVICE_GROUP" "$WORK_FILE"
    chmod 0640 "$WORK_FILE"
    stop_preflight
    systemd-run --quiet --unit="$PREFLIGHT_UNIT" \
        --uid="$SERVICE_USER" --gid="$SERVICE_GROUP" \
        --working-directory="$(dirname "$APPLICATION")" \
        --property="EnvironmentFile=$ENV_FILE" \
        /usr/bin/env \
        "$ZONES_VARIABLE=$WORK_FILE" \
        "$ADDRESS_VARIABLE=$PREFLIGHT_ADDRESS" \
        "$PORT_VARIABLE=$PREFLIGHT_PORT" \
        GSETTINGS_BACKEND=memory \
        /usr/local/bin/santafé "$APPLICATION"
    PREFLIGHT_ACTIVE=1
    if ! aguarde_txt "$PREFLIGHT_ADDRESS" "$PREFLIGHT_PORT" \
            "$DOMAIN" "$compact_spf" >/dev/null ||
            ! aguarde_txt "$PREFLIGHT_ADDRESS" "$PREFLIGHT_PORT" \
            "${DKIM_HOST}.${DOMAIN}" "$compact_expected" >/dev/null ||
            ! aguarde_assinatura "$PREFLIGHT_ADDRESS" "$PREFLIGHT_PORT" \
            "${DKIM_HOST}.${DOMAIN}" >/dev/null; then
        systemctl status "$PREFLIGHT_UNIT" --no-pager -l >&2 || true
        journalctl -u "$PREFLIGHT_UNIT" -n 80 --no-pager -l >&2 || true
        false
    fi
    stop_preflight

    install -o root -g "$SERVICE_GROUP" -m 0640 \
        "$WORK_FILE" "${ZONE_FILE}.novo"
    mv -f "${ZONE_FILE}.novo" "$ZONE_FILE"
    INSTALLED=1
    systemctl restart "$SERVICE"
fi

systemctl is-active --quiet "$SERVICE"

if ! aguarde_txt "$AUTHORITATIVE_ADDRESS" 53 \
        "$DOMAIN" "$compact_spf" >/dev/null; then
    printf 'ERRO: a autoridade não publicou o SPF Mailjet esperado.\n' >&2
    false
fi
if ! aguarde_txt "$AUTHORITATIVE_ADDRESS" 53 \
        "${DKIM_HOST}.${DOMAIN}" "$compact_expected" >/dev/null; then
    printf 'ERRO: a autoridade não publicou o DKIM Mailjet esperado.\n' >&2
    false
fi
if ! aguarde_assinatura "$AUTHORITATIVE_ADDRESS" 53 \
        "${DKIM_HOST}.${DOMAIN}" >/dev/null; then
    printf 'ERRO: a autoridade não publicou a RRSIG do DKIM Mailjet.\n' >&2
    false
fi

DONE=1
cleanup
trap - ERR INT TERM
printf 'SPF e DKIM Mailjet do Santafé publicados e assinados. Cópia: %s\n' \
    "$BACKUP_DIR"
printf 'Autoridade atualizada: %s; série de referência: %s.\n' \
    "$AUTHORITATIVE_ADDRESS" "$base_serial"
printf 'Entrega direta pelo IP 143.208.252.1 continua autorizada no mesmo SPF.\n'
