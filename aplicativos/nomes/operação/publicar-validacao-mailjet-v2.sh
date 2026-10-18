#!/usr/bin/env bash
set -Eeuo pipefail

SERVICE="nomes-autoridade.service"
ENV_FILE="/etc/santafe-nomes/nomes.env"
DOMAIN="xn--santaf-gva.dev.br."
AUTHORITATIVE_ADDRESS="143.208.252.1"
HOST="mailjet._d25ac9b6"
TOKEN="d25ac9b68479c83d7292b03c0b15fc8e"
FQDN="${HOST}.${DOMAIN}"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="/var/backups/santafe-mailjet-${STAMP}"
WORK_FILE="$(mktemp /var/tmp/santafe-mailjet-zonas.XXXXXX)"
INSTALLED=0
DONE=0

cleanup() {
    rm -f "$WORK_FILE" "${WORK_FILE}.novo"
}

rollback() {
    local code="$?"
    if [ "$DONE" -eq 1 ]; then
        cleanup
        exit 0
    fi
    printf 'ERRO: validação Mailjet interrompida na linha %s (código %s).\n' \
        "${BASH_LINENO[0]:-?}" "$code" >&2
    if [ "$INSTALLED" -eq 1 ] && [ -f "$BACKUP_DIR/zonas.fé" ]; then
        install -o root -g nomes-santafe -m 0640 \
            "$BACKUP_DIR/zonas.fé" "$ZONE_FILE"
        systemctl restart "$SERVICE" || true
        printf 'Zona anterior restaurada. Cópia: %s\n' "$BACKUP_DIR" >&2
    fi
    cleanup
    exit "$code"
}

trap rollback ERR INT TERM

test "$(id -u)" -eq 0
command -v awk >/dev/null
command -v dig >/dev/null
test -r "$ENV_FILE"

ZONE_FILE="$(sed -n 's/^NOMES_ZONAS_ARQUIVO=//p' "$ENV_FILE" | tail -n 1)"
test -n "$ZONE_FILE"
case "$ZONE_FILE" in
    /*) ;;
    *) printf 'ERRO: NOMES_ZONAS_ARQUIVO não é absoluto.\n' >&2; exit 1 ;;
esac
test -r "$ZONE_FILE"

mkdir -p "$BACKUP_DIR"
install -m 0600 "$ZONE_FILE" "$BACKUP_DIR/zonas.fé"
cp "$ZONE_FILE" "$WORK_FILE"

if ! grep -Fq "$TOKEN" "$WORK_FILE"; then
    base_serial="$(date +%Y%m%d)01"
    awk -v domain="$DOMAIN" -v host="$HOST" -v value="$TOKEN" \
        -v base="$base_serial" '
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
            print line
            if (in_zone && !inserted &&
                    line ~ /registros[[:space:]]*=[[:space:]]*\{/) {
                print "            { nome = \"" host "\", tipo = \"TXT\", dados ="
                print "                \"" value "\" },"
                inserted = 1
            }
        }
        END {
            if (!found_domain) {
                print "ERRO: zona Santafé não encontrada no arquivo ativo." > "/dev/stderr"
                exit 42
            }
            if (!inserted) {
                print "ERRO: tabela de registros da zona Santafé não encontrada." > "/dev/stderr"
                exit 43
            }
            if (!serial_done) {
                print "ERRO: série SOA da zona Santafé não encontrada." > "/dev/stderr"
                exit 44
            }
        }
    ' "$WORK_FILE" > "${WORK_FILE}.novo"
    mv "${WORK_FILE}.novo" "$WORK_FILE"

    /usr/local/bin/santafec -p "$WORK_FILE"
    install -o root -g nomes-santafe -m 0640 "$WORK_FILE" "${ZONE_FILE}.novo"
    mv -f "${ZONE_FILE}.novo" "$ZONE_FILE"
    INSTALLED=1
    systemctl restart "$SERVICE"
fi

systemctl is-active --quiet "$SERVICE"

answer=""
for _ in $(seq 1 40); do
    answer="$(dig +time=1 +tries=1 +short \
        @"$AUTHORITATIVE_ADDRESS" "$FQDN" TXT 2>/dev/null || true)"
    if grep -Fq "$TOKEN" <<<"$answer"; then
        break
    fi
    sleep 0.25
done
grep -Fq "$TOKEN" <<<"$answer"

signed="$(dig +time=2 +tries=2 @"$AUTHORITATIVE_ADDRESS" \
    "$FQDN" TXT +dnssec 2>/dev/null)"
grep -Fq 'RRSIG' <<<"$signed"

DONE=1
cleanup
trap - ERR INT TERM
printf 'Validação Mailjet do Santafé publicada e assinada. Cópia: %s\n' \
    "$BACKUP_DIR"
printf 'Nenhuma zona externa à plataforma foi alterada.\n'
