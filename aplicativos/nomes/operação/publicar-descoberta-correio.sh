#!/usr/bin/env bash

set -Eeuo pipefail

SERVICE="nomes-autoridade.service"
ENV_FILE="/etc/santafe-nomes/nomes.env"
DOMAIN="xn--santaf-gva.dev.br."
AUTHORITATIVE_ADDRESS="143.208.252.1"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="/var/backups/santafe-descoberta-correio-${STAMP}"
WORK_FILE="$(mktemp /var/tmp/santafe-descoberta-correio.XXXXXX)"
INSTALLED=0

cleanup() {
    rm -f -- "$WORK_FILE" "${WORK_FILE}.novo"
}

rollback() {
    local code="$?"
    trap - ERR INT TERM
    set +e
    printf 'ERRO: publicação dos registros SRV interrompida na linha %s (código %s).\n' \
        "${BASH_LINENO[0]:-?}" "$code" >&2
    if [[ "$INSTALLED" -eq 1 && -f "$BACKUP_DIR/zonas.fé" ]]; then
        install -o root -g nomes-santafe -m 0640 \
            "$BACKUP_DIR/zonas.fé" "$ZONE_FILE"
        systemctl restart "$SERVICE" || true
        printf 'Zona anterior restaurada. Cópia: %s\n' "$BACKUP_DIR" >&2
    fi
    cleanup
    exit "$code"
}

trap cleanup EXIT
trap rollback ERR INT TERM

[[ "$EUID" -eq 0 ]] || { echo "Execute com sudo." >&2; exit 1; }
command -v dig >/dev/null
[[ -r "$ENV_FILE" ]]

ZONE_FILE="$(sed -n 's/^NOMES_ZONAS_ARQUIVO=//p' "$ENV_FILE" | tail -n 1)"
[[ -n "$ZONE_FILE" && "$ZONE_FILE" == /* && -r "$ZONE_FILE" ]]

mkdir -p "$BACKUP_DIR"
install -m 0600 "$ZONE_FILE" "$BACKUP_DIR/zonas.fé"
cp "$ZONE_FILE" "$WORK_FILE"

present=0
for owner in _imaps._tcp _submissions._tcp _submission._tcp; do
    if grep -F "nome = \"${owner}\"" "$WORK_FILE" >/dev/null; then
        present=$((present + 1))
    fi
done

if [[ "$present" -ne 0 && "$present" -ne 3 ]]; then
    echo "A zona contém somente parte dos registros postais; nada foi alterado." >&2
    exit 1
fi

if [[ "$present" -eq 0 ]]; then
    old_serial="$(sed -n '0,/série = [0-9][0-9]*/{s/.*série = \([0-9][0-9]*\).*/\1/p}' "$WORK_FILE")"
    [[ -n "$old_serial" ]]
    base_serial="$(date +%Y%m%d)01"
    if [[ "$old_serial" -ge "$base_serial" ]]; then
        new_serial=$((old_serial + 1))
    else
        new_serial="$base_serial"
    fi
    sed -i "0,/série = ${old_serial}/s//série = ${new_serial}/" "$WORK_FILE"

    awk '
        !inserted && index($0, "tipo = \"MX\"") {
            print "            { nome = \"_imaps._tcp\", tipo = \"SRV\", dados = {"
            print "                prioridade = 0, peso = 1, porta = 993, alvo = \"@\" } },"
            print "            { nome = \"_submissions._tcp\", tipo = \"SRV\", dados = {"
            print "                prioridade = 0, peso = 1, porta = 465, alvo = \"@\" } },"
            print "            { nome = \"_submission._tcp\", tipo = \"SRV\", dados = {"
            print "                prioridade = 0, peso = 1, porta = 587, alvo = \"@\" } },"
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

wait_authority() {
    local answer counter
    for ((counter=1; counter<=80; counter++)); do
        answer="$(dig +tcp +time=1 +tries=1 +short \
            @"$AUTHORITATIVE_ADDRESS" "$DOMAIN" SOA 2>/dev/null || true)"
        [[ -z "$answer" ]] || return 0
        sleep 0.25
    done
    return 1
}

validate_srv() {
    local owner="$1" port="$2" answer signed counter
    for ((counter=1; counter<=40; counter++)); do
        answer="$(dig +tcp +time=1 +tries=1 +short \
            @"$AUTHORITATIVE_ADDRESS" "${owner}.${DOMAIN}" SRV \
            2>/dev/null || true)"
        if grep -Fx "0 1 ${port} ${DOMAIN}" <<<"$answer" >/dev/null; then
            signed="$(dig +tcp +time=2 +tries=2 \
                @"$AUTHORITATIVE_ADDRESS" "${owner}.${DOMAIN}" SRV +dnssec \
                2>/dev/null || true)"
            if grep -F 'RRSIG' <<<"$signed" >/dev/null; then return 0; fi
        fi
        sleep 0.25
    done
    return 1
}

if ! wait_authority; then
    echo "A autoridade não voltou a responder dentro do prazo." >&2
    false
fi
if ! validate_srv _imaps._tcp 993; then
    echo "O SRV de IMAPS não foi confirmado com RRSIG." >&2
    false
fi
if ! validate_srv _submissions._tcp 465; then
    echo "O SRV de submissão TLS não foi confirmado com RRSIG." >&2
    false
fi
if ! validate_srv _submission._tcp 587; then
    echo "O SRV de submissão STARTTLS não foi confirmado com RRSIG." >&2
    false
fi

INSTALLED=0
cleanup
trap - ERR INT TERM EXIT
printf 'Descoberta postal publicada e assinada. Cópia: %s\n' "$BACKUP_DIR"
printf 'IMAPS: 993/TLS; submissions: 465/TLS; submission: 587/STARTTLS.\n'
