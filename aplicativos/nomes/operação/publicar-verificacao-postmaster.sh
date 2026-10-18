#!/usr/bin/env bash
set -Eeuo pipefail

SERVICE="nomes-autoridade.service"
ENV_FILE="/etc/santafe-nomes/nomes.env"
DOMAIN="xn--santaf-gva.dev.br."
AUTHORITATIVE_ADDRESS="143.208.252.1"
TOKEN="google-site-verification=guvY1bhwgtxc2cvX9xdBk6InJ8p7rCDqm7c13ChT4z8"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="/var/backups/santafe-postmaster-${STAMP}"
WORK_FILE="$(mktemp /var/tmp/santafe-postmaster-zona.XXXXXX)"
INSTALLED=0
DONE=0

cleanup() {
    rm -f "$WORK_FILE"
}

rollback() {
    local code="$?"
    if [ "$DONE" -eq 1 ]; then
        cleanup
        exit 0
    fi
    printf 'ERRO: verificação Postmaster interrompida na linha %s (código %s).\n' \
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
command -v dig >/dev/null
test -r "$ENV_FILE"

ZONE_FILE="$(sed -n 's/^NOMES_ZONAS_ARQUIVO=//p' "$ENV_FILE" | tail -n 1)"
test -n "$ZONE_FILE"
case "$ZONE_FILE" in
    /*) ;;
    *) printf 'ERRO: NOMES_ZONAS_ARQUIVO não é um caminho absoluto.\n' >&2; exit 1 ;;
esac
test -r "$ZONE_FILE"

mkdir -p "$BACKUP_DIR"
install -m 0600 "$ZONE_FILE" "$BACKUP_DIR/zonas.fé"
cp "$ZONE_FILE" "$WORK_FILE"

if ! grep -Fq "$TOKEN" "$WORK_FILE"; then
    old_serial="$(sed -n '0,/série = [0-9][0-9]*/{s/.*série = \([0-9][0-9]*\).*/\1/p}' "$WORK_FILE")"
    test -n "$old_serial"
    base_serial="$(date +%Y%m%d)01"
    if [ "$old_serial" -ge "$base_serial" ]; then
        new_serial="$((old_serial + 1))"
    else
        new_serial="$base_serial"
    fi

    sed -i "0,/série = ${old_serial}/s//série = ${new_serial}/" "$WORK_FILE"

    awk -v token="$TOKEN" '
        !inserted && index($0, "{ nome = \"_dmarc\"") {
            print "            { nome = \"@\", tipo = \"TXT\", dados ="
            print "                \"" token "\" },"
            inserted = 1
        }
        { print }
        END { if (!inserted) exit 42 }
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
    answer="$(dig +time=1 +tries=1 +short @"$AUTHORITATIVE_ADDRESS" "$DOMAIN" TXT 2>/dev/null || true)"
    if grep -Fq "$TOKEN" <<<"$answer"; then
        break
    fi
    sleep 0.25
done
grep -Fq "$TOKEN" <<<"$answer"

signed="$(dig +time=2 +tries=2 @"$AUTHORITATIVE_ADDRESS" "$DOMAIN" TXT +dnssec 2>/dev/null)"
grep -Fq 'RRSIG' <<<"$signed"

public="$(dig +time=2 +tries=2 +short @"$AUTHORITATIVE_ADDRESS" "$DOMAIN" TXT 2>/dev/null)"
grep -Fq "$TOKEN" <<<"$public"

DONE=1
cleanup
trap - ERR INT TERM
printf 'Verificação do Google publicada e assinada. Cópia: %s\n' "$BACKUP_DIR"
printf 'TXT: %s\n' "$TOKEN"
