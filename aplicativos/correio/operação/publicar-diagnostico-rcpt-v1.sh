#!/usr/bin/env bash

set -Eeuo pipefail

PACKAGE="/tmp/santafe-diagnostico-rcpt-20260901-v1.tar.gz"
EXPECTED_HASH="240a53534154cfb1caf2b389711215a56cc2c7dd7b75d5537ab010241beb15ca"
SERVICE="correio-agencia.service"
INSTALLED_BIBF="/usr/local/share/santafé/1.0/bibf"
SOURCE_ROOT="/home/${SUDO_USER:-rafael}/santafe-fonte"
WORK=""
ROOT=""
BACKUP=""
PUBLISHING=0

cleanup() {
    if [[ -n "$WORK" && -d "$WORK" ]]; then rm -rf -- "$WORK"; fi
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
        echo "ERRO: diagnóstico RCPT interrompido; restaurando."
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

run_tests() {
    local root="$1"
    local lua_path="$root/bibs/bibf/?.fé;$root/bibs/bibf/?/?.fé;$INSTALLED_BIBF/?.fé;$INSTALLED_BIBF/?/?.fé;;"
    local lua_cpath="/usr/local/lib/santafé/1.0/bibc/?.so;;"
    (
        cd "$root"
        env GSETTINGS_BACKEND=memory LUA_PATH="$lua_path" \
            LUA_CPATH="$lua_cpath" \
            /usr/local/bin/santafé testes/bibf/teste_correio.fé
        env GSETTINGS_BACKEND=memory LUA_PATH="$lua_path" \
            LUA_CPATH="$lua_cpath" \
            /usr/local/bin/santafé \
                testes/bibc/teste_correio_submissão_smtp.fé
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

[[ "$EUID" -eq 0 ]] || { echo "Execute com sudo." >&2; exit 1; }
echo "Publicador Correio 0.5.3 — diagnóstico exato de RCPT"
[[ -f "$PACKAGE" ]] || { echo "Pacote ausente: $PACKAGE" >&2; exit 1; }
ACTUAL_HASH="$(sha256sum "$PACKAGE" | awk '{print $1}')"
[[ "$ACTUAL_HASH" == "$EXPECTED_HASH" ]] || {
    echo "A soma do pacote não confere; nada foi alterado." >&2
    exit 1
}
systemctl is-active --quiet "$SERVICE"

WORK="$(mktemp -d /tmp/santafe-diagnostico-rcpt-publicacao.XXXXXX)"
tar -xzf "$PACKAGE" -C "$WORK"
ROOT="$WORK/source"
REQUIRED=(
    bibs/bibf/correio.fé
    testes/bibf/teste_correio.fé
    testes/bibc/teste_correio_submissão_smtp.fé
    testes/recursos/tls-local-certificado.pem
    testes/recursos/tls-local-chave.pem
)
for relative in "${REQUIRED[@]}"; do
    [[ -f "$ROOT/$relative" ]] || {
        echo "Arquivo ausente no pacote: $relative" >&2
        exit 1
    }
done

echo "==> Validando o rastro detalhado sem senha nem corpo"
/usr/local/bin/santafec -p "$ROOT/bibs/bibf/correio.fé"
grep -Fq 'versão = "0.5.3"' "$ROOT/bibs/bibf/correio.fé"
grep -Fq 'correio.destinatárioMalformado' "$ROOT/bibs/bibf/correio.fé"
run_tests "$ROOT"

BACKUP="/var/backups/santafe-diagnostico-rcpt-$(date +%Y%m%d-%H%M%S)"
install -d -m 0700 "$BACKUP"
BACKUP_PATHS=(
    usr/local/share/santafé/1.0/bibf/correio.fé
    home/${SUDO_USER:-rafael}/santafe-fonte/bibs/bibf/correio.fé
    home/${SUDO_USER:-rafael}/santafe-fonte/testes/bibf/teste_correio.fé
    home/${SUDO_USER:-rafael}/santafe-fonte/testes/bibc/teste_correio_submissão_smtp.fé
)
for relative in "${BACKUP_PATHS[@]}"; do
    [[ -f "/$relative" ]] || {
        echo "Arquivo de produção ausente: /$relative" >&2
        exit 1
    }
done
tar -czf "$BACKUP/antes.tar.gz" -C / "${BACKUP_PATHS[@]}"

PUBLISHING=1
echo "==> Instalando o diagnóstico e reiniciando somente a Agência"
systemctl stop "$SERVICE"
install -o root -g root -m 0644 "$ROOT/bibs/bibf/correio.fé" \
    "$INSTALLED_BIBF/correio.fé"
systemctl start "$SERVICE"
wait_for_agency
/usr/local/bin/santafé -e \
    'local C=importe "correio"; garanta(C.versão=="0.5.3"); mostre("CORREIO_DIAGNOSTICO_RCPT_OK")'
validate_live

echo "==> Atualizando os fontes correspondentes no servidor"
OWNER="${SUDO_USER:-rafael}"
GROUP="$(id -gn "$OWNER")"
for relative in bibs/bibf/correio.fé testes/bibf/teste_correio.fé \
    testes/bibc/teste_correio_submissão_smtp.fé; do
    install -o "$OWNER" -g "$GROUP" -m 0644 \
        "$ROOT/$relative" "$SOURCE_ROOT/$relative"
done

systemctl is-active --quiet "$SERVICE"
PUBLISHING=0
trap - ERR
echo "Diagnóstico RCPT publicado e validado. Cópia: $BACKUP"
echo "Uma nova tentativa mostrará o caminho rejeitado e a causa exata."
