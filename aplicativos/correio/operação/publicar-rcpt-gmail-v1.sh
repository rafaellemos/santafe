#!/usr/bin/env bash

set -Eeuo pipefail

PACKAGE="/tmp/santafe-rcpt-gmail-20260901-v1.tar.gz"
EXPECTED_HASH="8b17a1fcbbce36e35c80f151ab57e4125dd09a07a6f4f0547c9652293421f6bf"
SERVICE="correio-agencia.service"
INSTALLED_BIBF="/usr/local/share/santafé/1.0/bibf"
INSTALLED_MANUAL="/var/www/santafé.dev.br/estático/manual/index.html"
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
        echo "ERRO: correção RCPT/Gmail interrompida; restaurando."
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

run_smtp_tests() {
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

validate_manual() {
    local root="$1"
    (
        cd "$root/site"
        python3 validar-manual.py manual.html \
            --compilador /usr/local/bin/santafec
    )
}

validate_live() {
    printf 'EHLO auditoria.local\r\nQUIT\r\n' > "$WORK/smtp-input.txt"
    timeout 10 openssl s_client -connect 127.0.0.1:465 \
        -servername xn--santaf-gva.dev.br -quiet \
        < "$WORK/smtp-input.txt" > "$WORK/smtp-output.txt" 2>/dev/null || true
    grep -Fq '250-SMTPUTF8' "$WORK/smtp-output.txt"
    grep -Fq '221 2.0.0' "$WORK/smtp-output.txt"
    curl -kfsS --max-time 8 -H 'Host: xn--santaf-gva.dev.br' \
        https://127.0.0.1/estático/manual/ -o "$WORK/manual-live.html"
    grep -Fq '&quot;josé&quot;@xn--santaf-gva.dev.br' \
        "$WORK/manual-live.html"
}

trap cleanup EXIT
trap 'restore_previous "$?" "$LINENO" "$BASH_COMMAND"' ERR

[[ "$EUID" -eq 0 ]] || {
    echo "Execute com sudo." >&2
    exit 1
}

echo "Publicador Correio 0.5.2 — RCPT SMTPUTF8 do Gmail"
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

WORK="$(mktemp -d /tmp/santafe-rcpt-gmail-publicacao.XXXXXX)"
tar -xzf "$PACKAGE" -C "$WORK"
ROOT="$WORK/source"

REQUIRED=(
    bibs/bibf/correio.fé
    aplicativos/correio/LEIA-ME.md
    bibs/bibf/correio/LEIA-ME.md
    docs/ARQUITETURA-DO-ECOSSISTEMA.md
    testes/bibf/teste_correio.fé
    testes/bibc/teste_correio_submissão_smtp.fé
    testes/recursos/tls-local-certificado.pem
    testes/recursos/tls-local-chave.pem
    site/manual.html
    site/validar-manual.py
)
for relative in "${REQUIRED[@]}"; do
    [[ -f "$ROOT/$relative" ]] || {
        echo "Arquivo ausente no pacote: $relative" >&2
        exit 1
    }
done

echo "==> Validando RCPT entre aspas, SMTPUTF8, rastro e manual"
/usr/local/bin/santafec -p "$ROOT/bibs/bibf/correio.fé"
/usr/local/bin/santafec -p \
    "$ROOT/testes/bibc/teste_correio_submissão_smtp.fé"
grep -Fq 'versão = "0.5.2"' "$ROOT/bibs/bibf/correio.fé"
grep -Fq 'normalizeCaminhoSMTP' "$ROOT/bibs/bibf/correio.fé"
run_smtp_tests "$ROOT"
validate_manual "$ROOT"

BACKUP="/var/backups/santafe-rcpt-gmail-$(date +%Y%m%d-%H%M%S)"
install -d -m 0700 "$BACKUP"
BACKUP_PATHS=(
    usr/local/share/santafé/1.0/bibf/correio.fé
    var/www/santafé.dev.br/estático/manual/index.html
    home/${SUDO_USER:-rafael}/santafe-fonte/bibs/bibf/correio.fé
    home/${SUDO_USER:-rafael}/santafe-fonte/aplicativos/correio/LEIA-ME.md
    home/${SUDO_USER:-rafael}/santafe-fonte/bibs/bibf/correio/LEIA-ME.md
    home/${SUDO_USER:-rafael}/santafe-fonte/docs/ARQUITETURA-DO-ECOSSISTEMA.md
    home/${SUDO_USER:-rafael}/santafe-fonte/testes/bibf/teste_correio.fé
    home/${SUDO_USER:-rafael}/santafe-fonte/testes/bibc/teste_correio_submissão_smtp.fé
    home/${SUDO_USER:-rafael}/santafe-fonte/site-sfdev/manual.html
    home/${SUDO_USER:-rafael}/santafe-fonte/site-sfdev/validar-manual.py
)
for relative in "${BACKUP_PATHS[@]}"; do
    [[ -f "/$relative" ]] || {
        echo "Arquivo de produção ausente: /$relative" >&2
        exit 1
    }
done
tar -czf "$BACKUP/antes.tar.gz" -C / "${BACKUP_PATHS[@]}"

PUBLISHING=1
echo "==> Instalando o Correio 0.5.2 e reiniciando somente a Agência"
systemctl stop "$SERVICE"
install -o root -g root -m 0644 "$ROOT/bibs/bibf/correio.fé" \
    "$INSTALLED_BIBF/correio.fé"
install -o www-data -g www-data -m 0644 "$ROOT/site/manual.html" \
    "$INSTALLED_MANUAL"
systemctl start "$SERVICE"
wait_for_agency

/usr/local/bin/santafé -e \
    'local C=importe "correio"; garanta(C.versão=="0.5.2"); mostre("CORREIO_RCPT_GMAIL_OK")'
validate_live

echo "==> Atualizando a árvore-fonte do servidor"
OWNER="${SUDO_USER:-rafael}"
GROUP="$(id -gn "$OWNER")"
SOURCE_FILES=(
    bibs/bibf/correio.fé
    aplicativos/correio/LEIA-ME.md
    bibs/bibf/correio/LEIA-ME.md
    docs/ARQUITETURA-DO-ECOSSISTEMA.md
    testes/bibf/teste_correio.fé
    testes/bibc/teste_correio_submissão_smtp.fé
)
for relative in "${SOURCE_FILES[@]}"; do
    install -o "$OWNER" -g "$GROUP" -m 0644 \
        "$ROOT/$relative" "$SOURCE_ROOT/$relative"
done
install -o "$OWNER" -g "$GROUP" -m 0644 "$ROOT/site/manual.html" \
    "$SOURCE_ROOT/site-sfdev/manual.html"
install -o "$OWNER" -g "$GROUP" -m 0644 \
    "$ROOT/site/validar-manual.py" \
    "$SOURCE_ROOT/site-sfdev/validar-manual.py"

systemctl is-active --quiet "$SERVICE"
PUBLISHING=0
trap - ERR
echo "RCPT SMTPUTF8 do Gmail publicado e validado. Cópia: $BACKUP"
echo "A forma entre aspas agora alcança a mesma caixa Unicode canônica."
