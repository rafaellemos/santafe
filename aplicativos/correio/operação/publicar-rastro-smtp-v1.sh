#!/usr/bin/env bash

set -Eeuo pipefail

PACKAGE="/tmp/santafe-rastro-smtp-20260901-v1.tar.gz"
EXPECTED_HASH="9057a2839448751072b700965a18f5ea828c1e106f91da610d2bc09157e42465"
SERVICE="correio-agencia.service"
INSTALLED_BIBF="/usr/local/share/santafé/1.0/bibf"
SOURCE_ROOT="/home/${SUDO_USER:-rafael}/santafe-fonte"
WORK=""
ROOT=""
BACKUP=""
PUBLISHING=0

cleanup() {
    if [[ -n "$WORK" && -d "$WORK" ]]; then
        rm -rf -- "$WORK"
    fi
}

restore_previous() {
    local code="${1:-1}"
    local line="${2:-desconhecida}"
    local command="${3:-desconhecido}"
    trap - ERR
    set +e
    printf 'Falha na linha %s (código %s): %s\n' \
        "$line" "$code" "$command" >&2
    if [[ "$PUBLISHING" -eq 1 && -f "$BACKUP/antes.tar.gz" ]]; then
        echo "ERRO: rastro SMTP interrompido; restaurando."
        systemctl stop "$SERVICE" >/dev/null 2>&1 || true
        tar -xzf "$BACKUP/antes.tar.gz" -C /
        systemctl start "$SERVICE" >/dev/null 2>&1 || true
        echo "Versão anterior restaurada. Cópia: $BACKUP"
    fi
    exit "$code"
}

wait_for_agency() {
    local attempt
    for ((attempt=1; attempt<=160; attempt++)); do
        if systemctl is-active --quiet "$SERVICE" &&
           [[ -n "$(ss -ltnH 'sport = :465')" ]] &&
           [[ -n "$(ss -ltnH 'sport = :587')" ]]; then
            return 0
        fi
        if systemctl is-failed --quiet "$SERVICE"; then break; fi
        sleep 0.25
    done
    systemctl status "$SERVICE" --no-pager -l >&2 || true
    journalctl -u "$SERVICE" -n 120 --no-pager -l >&2 || true
    return 1
}

run_test() {
    local root="$1"
    (
        cd "$root"
        env GSETTINGS_BACKEND=memory \
            LUA_PATH="$root/bibs/bibf/?.fé;$root/bibs/bibf/?/?.fé;$INSTALLED_BIBF/?.fé;$INSTALLED_BIBF/?/?.fé;;" \
            LUA_CPATH="/usr/local/lib/santafé/1.0/bibc/?.so;;" \
            /usr/local/bin/santafé testes/bibf/teste_correio.fé
    )
}

validate_live() {
    printf 'EHLO auditoria.local\r\nQUIT\r\n' > "$WORK/smtp-input.txt"
    timeout 10 openssl s_client -connect 127.0.0.1:465 \
        -servername xn--santaf-gva.dev.br -quiet \
        < "$WORK/smtp-input.txt" > "$WORK/smtp-output.txt" 2>/dev/null || true
    grep -Fq '250-SMTPUTF8' "$WORK/smtp-output.txt"
    grep -Fq '221 2.0.0' "$WORK/smtp-output.txt"
}

trap cleanup EXIT
trap 'restore_previous "$?" "$LINENO" "$BASH_COMMAND"' ERR

[[ "$EUID" -eq 0 ]] || {
    echo "Execute com sudo." >&2
    exit 1
}

echo "Publicador Correio 0.5.1 — rastro SMTP seguro"
[[ -f "$PACKAGE" ]] || { echo "Pacote ausente: $PACKAGE" >&2; exit 1; }
ACTUAL_HASH="$(sha256sum "$PACKAGE" | awk '{print $1}')"
[[ "$ACTUAL_HASH" == "$EXPECTED_HASH" ]] || {
    echo "A soma do pacote não confere; nada foi alterado." >&2
    exit 1
}
systemctl is-active --quiet "$SERVICE" || {
    echo "$SERVICE não está ativo; nada foi alterado." >&2
    exit 1
}

WORK="$(mktemp -d /tmp/santafe-rastro-smtp-publicacao.XXXXXX)"
tar -xzf "$PACKAGE" -C "$WORK"
ROOT="$WORK/source"

REQUIRED=(
    bibs/bibf/correio.fé
    testes/bibf/teste_correio.fé
    testes/recursos/tls-local-certificado.pem
    testes/recursos/tls-local-chave.pem
)
for relative in "${REQUIRED[@]}"; do
    [[ -f "$ROOT/$relative" ]] || {
        echo "Arquivo ausente no pacote: $relative" >&2
        exit 1
    }
done

echo "==> Validando o rastro sem argumentos, credenciais ou conteúdo"
/usr/local/bin/santafec -p "$ROOT/bibs/bibf/correio.fé"
grep -Fq 'versão = "0.5.1"' "$ROOT/bibs/bibf/correio.fé"
grep -Fq 'correio.comandoRecusado' "$ROOT/bibs/bibf/correio.fé"
run_test "$ROOT"

BACKUP="/var/backups/santafe-rastro-smtp-$(date +%Y%m%d-%H%M%S)"
install -d -m 0700 "$BACKUP"
BACKUP_PATHS=(
    usr/local/share/santafé/1.0/bibf/correio.fé
    home/${SUDO_USER:-rafael}/santafe-fonte/bibs/bibf/correio.fé
)
for relative in "${BACKUP_PATHS[@]}"; do
    [[ -f "/$relative" ]] || {
        echo "Arquivo de produção ausente: /$relative" >&2
        exit 1
    }
done
tar -czf "$BACKUP/antes.tar.gz" -C / "${BACKUP_PATHS[@]}"

PUBLISHING=1
echo "==> Instalando somente o núcleo postal e reiniciando a Agência"
systemctl stop "$SERVICE"
install -o root -g root -m 0644 "$ROOT/bibs/bibf/correio.fé" \
    "$INSTALLED_BIBF/correio.fé"
systemctl start "$SERVICE"
wait_for_agency

/usr/local/bin/santafé -e \
    'local C=importe "correio"; garanta(C.versão=="0.5.1"); mostre("CORREIO_RASTRO_SMTP_OK")'
validate_live

echo "==> Atualizando a árvore-fonte do servidor"
OWNER="${SUDO_USER:-rafael}"
GROUP="$(id -gn "$OWNER")"
install -o "$OWNER" -g "$GROUP" -m 0644 \
    "$ROOT/bibs/bibf/correio.fé" \
    "$SOURCE_ROOT/bibs/bibf/correio.fé"
install -o "$OWNER" -g "$GROUP" -m 0644 \
    "$ROOT/testes/bibf/teste_correio.fé" \
    "$SOURCE_ROOT/testes/bibf/teste_correio.fé"

systemctl is-active --quiet "$SERVICE"
PUBLISHING=0
trap - ERR
echo "Rastro SMTP seguro publicado e validado. Cópia: $BACKUP"
echo "Repita o envio no Gmail; o PULSO indicará comando e código exatos."
