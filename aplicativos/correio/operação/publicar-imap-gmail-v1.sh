#!/usr/bin/env bash

set -Eeuo pipefail

PACKAGE="/tmp/santafe-imap-gmail-20260901-v1.tar.gz"
EXPECTED_HASH="fef501be4afb9e7a5e1529b5639da1f7e26652d852485daec11bac65bd090774"
SERVICE="correio-imap.service"
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
        echo "ERRO: correção Gmail/IMAP interrompida; restaurando."
        systemctl stop "$SERVICE" >/dev/null 2>&1 || true
        tar -xzf "$BACKUP/antes.tar.gz" -C /
        systemctl start "$SERVICE" >/dev/null 2>&1 || true
        echo "Versão anterior restaurada. Cópia: $BACKUP"
    fi
    exit "$code"
}

wait_for_imap() {
    local attempt
    for ((attempt=1; attempt<=160; attempt++)); do
        if systemctl is-active --quiet "$SERVICE" &&
           [[ -n "$(ss -ltnH 'sport = :993')" ]]; then
            return 0
        fi
        if systemctl is-failed --quiet "$SERVICE"; then break; fi
        sleep 0.25
    done
    systemctl status "$SERVICE" --no-pager -l >&2 || true
    journalctl -u "$SERVICE" -n 120 --no-pager -l >&2 || true
    return 1
}

prepare_test_tls() {
    local root="$1"
    install -d "$root/testes/recursos"
    openssl req -x509 -newkey rsa:2048 -nodes -days 1 \
        -subj '/CN=localhost' \
        -keyout "$root/testes/recursos/tls-local-chave.pem" \
        -out "$root/testes/recursos/tls-local-certificado.pem" \
        >/dev/null 2>&1
    chmod 0600 "$root/testes/recursos/tls-local-chave.pem"
}

run_imap_test() {
    local root="$1"
    local port="$2"
    local lua_path="$root/bibs/bibf/?.fé;$root/bibs/bibf/?/?.fé;$INSTALLED_BIBF/?.fé;$INSTALLED_BIBF/?/?.fé;;"
    /usr/local/bin/santafec -p "$root/bibs/bibf/correio/imap.fé"
    /usr/local/bin/santafec -p \
        "$root/testes/integração/servidor_imap_memória.fé"
    (
        cd "$root"
        env GSETTINGS_BACKEND=memory PYTHONDONTWRITEBYTECODE=1 \
            LUA_PATH="$lua_path" \
            LUA_CPATH="/usr/local/lib/santafé/1.0/bibc/?.so;;" \
            python3 testes/integração/validar_imap.py \
                --santafe /usr/local/bin/santafé --porta "$port"
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
    printf 'a1 CAPABILITY\r\na2 LOGOUT\r\n' > "$WORK/imap-input.txt"
    timeout 10 openssl s_client -connect 127.0.0.1:993 \
        -servername xn--santaf-gva.dev.br -quiet \
        < "$WORK/imap-input.txt" > "$WORK/imap-output.txt" 2>/dev/null || true
    grep -Fq 'ENABLE UTF8=ACCEPT' "$WORK/imap-output.txt"
    if grep -Fq 'UTF8=ONLY' "$WORK/imap-output.txt"; then
        echo "O IMAP ainda anuncia UTF8=ONLY." >&2
        return 1
    fi
    curl -kfsS --max-time 8 -H 'Host: xn--santaf-gva.dev.br' \
        https://127.0.0.1/estático/manual/ -o "$WORK/manual-live.html"
    grep -Fq 'UTF8=ACCEPT' "$WORK/manual-live.html"
}

trap cleanup EXIT
trap 'restore_previous "$?" "$LINENO" "$BASH_COMMAND"' ERR

[[ "$EUID" -eq 0 ]] || {
    echo "Execute com sudo." >&2
    exit 1
}

echo "Publicador Correio IMAP 0.5.1 — interoperabilidade Gmail/Apple"
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

WORK="$(mktemp -d /tmp/santafe-imap-gmail-publicacao.XXXXXX)"
tar -xzf "$PACKAGE" -C "$WORK"
ROOT="$WORK/source"
prepare_test_tls "$ROOT"

REQUIRED=(
    bibs/bibf/correio/imap.fé
    aplicativos/correio/LEIA-ME.md
    bibs/bibf/correio/LEIA-ME.md
    docs/ARQUITETURA-DO-ECOSSISTEMA.md
    testes/integração/validar_imap.py
    testes/integração/servidor_imap_memória.fé
    site/manual.html
    site/validar-manual.py
)
for relative in "${REQUIRED[@]}"; do
    [[ -f "$ROOT/$relative" ]] || {
        echo "Arquivo ausente no pacote: $relative" >&2
        exit 1
    }
done

echo "==> Validando o fluxo Gmail, o fluxo ENABLE e o manual"
grep -Fq 'versão = "0.5.1"' "$ROOT/bibs/bibf/correio/imap.fé"
grep -Fq 'UTF8=ACCEPT' "$ROOT/bibs/bibf/correio/imap.fé"
if grep -Fq 'UTF8=ONLY' "$ROOT/bibs/bibf/correio/imap.fé"; then
    echo "O fonte ainda contém UTF8=ONLY." >&2
    exit 1
fi
run_imap_test "$ROOT" 19995
validate_manual "$ROOT"

BACKUP="/var/backups/santafe-imap-gmail-$(date +%Y%m%d-%H%M%S)"
install -d -m 0700 "$BACKUP"
BACKUP_PATHS=(
    usr/local/share/santafé/1.0/bibf/correio/imap.fé
    var/www/santafé.dev.br/estático/manual/index.html
    home/${SUDO_USER:-rafael}/santafe-fonte/bibs/bibf/correio/imap.fé
    home/${SUDO_USER:-rafael}/santafe-fonte/aplicativos/correio/LEIA-ME.md
    home/${SUDO_USER:-rafael}/santafe-fonte/bibs/bibf/correio/LEIA-ME.md
    home/${SUDO_USER:-rafael}/santafe-fonte/docs/ARQUITETURA-DO-ECOSSISTEMA.md
    home/${SUDO_USER:-rafael}/santafe-fonte/testes/integração/validar_imap.py
    home/${SUDO_USER:-rafael}/santafe-fonte/testes/integração/servidor_imap_memória.fé
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
echo "==> Instalando somente o IMAP 0.5.1 e o manual"
systemctl stop "$SERVICE"
install -o root -g root -m 0644 "$ROOT/bibs/bibf/correio/imap.fé" \
    "$INSTALLED_BIBF/correio/imap.fé"
install -o www-data -g www-data -m 0644 "$ROOT/site/manual.html" \
    "$INSTALLED_MANUAL"
systemctl start "$SERVICE"
wait_for_imap

/usr/local/bin/santafé -e \
    'local I=importe "correio.imap"; garanta(I.versão=="0.5.1"); mostre("IMAP_GMAIL_0_5_1_OK")'
run_imap_test "$ROOT" 19996
validate_manual "$ROOT"
validate_live

echo "==> Atualizando a árvore-fonte do servidor"
OWNER="${SUDO_USER:-rafael}"
GROUP="$(id -gn "$OWNER")"
SOURCE_FILES=(
    bibs/bibf/correio/imap.fé
    aplicativos/correio/LEIA-ME.md
    bibs/bibf/correio/LEIA-ME.md
    docs/ARQUITETURA-DO-ECOSSISTEMA.md
    testes/integração/validar_imap.py
    testes/integração/servidor_imap_memória.fé
)
for relative in "${SOURCE_FILES[@]}"; do
    install -o "$OWNER" -g "$GROUP" -m 0644 \
        "$ROOT/$relative" "$SOURCE_ROOT/$relative"
done
install -o "$OWNER" -g "$GROUP" -m 0644 "$ROOT/site/manual.html" \
    "$SOURCE_ROOT/site-sfdev/manual.html"
install -o "$OWNER" -g "$GROUP" -m 0644 "$ROOT/site/validar-manual.py" \
    "$SOURCE_ROOT/site-sfdev/validar-manual.py"

systemctl is-active --quiet "$SERVICE"
PUBLISHING=0
trap - ERR
echo "Correio IMAP 0.5.1 publicado e validado. Cópia: $BACKUP"
echo "Gmail pode selecionar caixas sem ENABLE; clientes modernos continuam usando ENABLE."
