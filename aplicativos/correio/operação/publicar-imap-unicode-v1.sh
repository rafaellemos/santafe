#!/usr/bin/env bash

set -Eeuo pipefail

PACKAGE="/tmp/santafe-imap-unicode-20260901-v1.tar.gz"
EXPECTED_HASH="b5b85d6eee9af5498a477d248ac5e6fa615026e116006c01fd7e97e314171782"
INSTALLED_BIBF="/usr/local/share/santafé/1.0/bibf"
INSTALLED_MANUAL="/var/www/santafé.dev.br/estático/manual/index.html"
SOURCE_ROOT="/home/${SUDO_USER:-rafael}/santafe-fonte"

WORK=""
ROOT=""
BACKUP=""
PUBLISHING=0
CREATED_PATHS=()

SERVICES=(
    correio-recebedor.service
    correio-agencia.service
    correio-imap.service
    carteiro.service
)

cleanup() {
    if [[ -n "$WORK" && -d "$WORK" ]]; then
        rm -rf -- "$WORK"
    fi
}

start_services() {
    systemctl start correio-recebedor.service
    systemctl start correio-agencia.service
    systemctl start correio-imap.service
    systemctl start carteiro.service
    systemctl start correio-envios.timer
}

stop_services() {
    systemctl stop correio-envios.timer
    systemctl stop correio-envios.service >/dev/null 2>&1 || true
    systemctl stop carteiro.service
    systemctl stop correio-imap.service
    systemctl stop correio-agencia.service
    systemctl stop correio-recebedor.service
}

restore_previous() {
    local code="${1:-1}"
    local line="${2:-desconhecida}"
    local command="${3:-desconhecido}"
    trap - ERR
    set +e
    printf 'Falha na linha %s (código %s): %s\n' \
        "$line" "$code" "$command" >&2
    if [[ "$PUBLISHING" -eq 1 && -n "$BACKUP" && \
          -f "$BACKUP/antes.tar.gz" ]]; then
        echo "ERRO: publicação Unicode interrompida; restaurando a versão anterior."
        stop_services >/dev/null 2>&1 || true
        tar -xzf "$BACKUP/antes.tar.gz" -C /
        for relative in "${CREATED_PATHS[@]}"; do
            rm -f -- "/$relative"
        done
        start_services >/dev/null 2>&1 || true
        echo "Versão anterior restaurada. Cópia de segurança: $BACKUP"
    fi
    exit "$code"
}

wait_for_service() {
    local service="$1"
    local port="$2"
    local attempt
    for ((attempt=1; attempt<=160; attempt++)); do
        if systemctl is-active --quiet "$service" &&
           [[ -n "$(ss -ltnH "sport = :$port")" ]]; then
            return 0
        fi
        if systemctl is-failed --quiet "$service"; then break; fi
        sleep 0.25
    done
    systemctl status "$service" --no-pager -l >&2 || true
    journalctl -u "$service" -n 120 --no-pager -l >&2 || true
    return 1
}

run_source_tests() {
    local root="$1"
    local port="$2"
    local lua_path="$root/bibs/bibf/?.fé;$root/bibs/bibf/?/?.fé;$INSTALLED_BIBF/?.fé;$INSTALLED_BIBF/?/?.fé;;"
    local lua_cpath="/usr/local/lib/santafé/1.0/bibc/?.so;;"

    /usr/local/bin/santafec -p "$root/bibs/bibf/correio.fé"
    /usr/local/bin/santafec -p "$root/bibs/bibf/correio/agência.fé"
    /usr/local/bin/santafec -p "$root/bibs/bibf/correio/imap.fé"
    /usr/local/bin/santafec -p \
        "$root/testes/integração/servidor_imap_memória.fé"
    PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
        "$root/testes/integração/validar_imap.py"

    env GSETTINGS_BACKEND=memory LUA_PATH="$lua_path" LUA_CPATH="$lua_cpath" \
        /usr/local/bin/santafé \
        "$root/testes/bibf/teste_correio_agência.fé"
    env GSETTINGS_BACKEND=memory LUA_PATH="$lua_path" LUA_CPATH="$lua_cpath" \
        /usr/local/bin/santafé \
        "$root/testes/bibf/teste_correio_mime.fé"
    env GSETTINGS_BACKEND=memory LUA_PATH="$lua_path" LUA_CPATH="$lua_cpath" \
        /usr/local/bin/santafé \
        "$root/testes/bibf/teste_correio_seguranca.fé"
    env GSETTINGS_BACKEND=memory LUA_PATH="$lua_path" LUA_CPATH="$lua_cpath" \
        /usr/local/bin/santafé \
        "$root/testes/bibc/teste_correio_submissão_smtp.fé"
    (
        cd "$root"
        env GSETTINGS_BACKEND=memory PYTHONDONTWRITEBYTECODE=1 \
            LUA_PATH="$lua_path" LUA_CPATH="$lua_cpath" \
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

validate_live_protocols() {
    local server_name="xn--santaf-gva.dev.br"

    printf 'a1 CAPABILITY\r\na2 LOGOUT\r\n' > "$WORK/imap-input.txt"
    timeout 10 openssl s_client -connect 127.0.0.1:993 \
        -servername "$server_name" -quiet \
        < "$WORK/imap-input.txt" > "$WORK/imap-output.txt" 2>/dev/null || true
    grep -Fq 'ENABLE UTF8=ONLY' "$WORK/imap-output.txt"

    printf 'EHLO teste.local\r\nQUIT\r\n' > "$WORK/smtp-input.txt"
    timeout 10 openssl s_client -connect 127.0.0.1:465 \
        -servername "$server_name" -quiet \
        < "$WORK/smtp-input.txt" > "$WORK/smtp465-output.txt" 2>/dev/null || true
    grep -Fq 'SMTPUTF8' "$WORK/smtp465-output.txt"

    timeout 10 openssl s_client -starttls smtp -connect 127.0.0.1:587 \
        -servername "$server_name" -quiet \
        < "$WORK/smtp-input.txt" > "$WORK/smtp587-output.txt" 2>/dev/null || true
    grep -Fq 'SMTPUTF8' "$WORK/smtp587-output.txt"

    curl -fsS --max-time 8 http://127.0.0.1:7100/carteiro/ \
        -o "$WORK/carteiro-live.html"
    curl -kfsS --max-time 8 -H 'Host: xn--santaf-gva.dev.br' \
        https://127.0.0.1/estático/manual/ \
        -o "$WORK/manual-live.html"
    grep -Fq 'UTF8=ONLY' "$WORK/manual-live.html"
    grep -Fq 'inspecioneCabeçalhos' "$WORK/manual-live.html"
}

trap cleanup EXIT
trap 'restore_previous "$?" "$LINENO" "$BASH_COMMAND"' ERR

[[ "$EUID" -eq 0 ]] || {
    echo "Execute com sudo." >&2
    exit 1
}

echo "Publicador Correio/IMAP Unicode 0.5.0 — RFC 6531, 6532 e 6855"
[[ -f "$PACKAGE" ]] || {
    echo "Pacote ausente: $PACKAGE" >&2
    exit 1
}
ACTUAL_HASH="$(sha256sum "$PACKAGE" | awk '{print $1}')"
[[ "$ACTUAL_HASH" == "$EXPECTED_HASH" ]] || {
    echo "A soma do pacote não confere; nada foi alterado." >&2
    exit 1
}

for service in "${SERVICES[@]}"; do
    systemctl is-active --quiet "$service" || {
        echo "$service não está ativo; nada foi alterado." >&2
        exit 1
    }
done
systemctl is-active --quiet correio-envios.timer || {
    echo "correio-envios.timer não está ativo; nada foi alterado." >&2
    exit 1
}

WORK="$(mktemp -d /tmp/santafe-imap-unicode-publicacao.XXXXXX)"
tar -xzf "$PACKAGE" -C "$WORK"
ROOT="$WORK/source"

install -d "$ROOT/testes/recursos"
openssl req -x509 -newkey rsa:2048 -nodes -days 1 \
    -subj '/CN=localhost' \
    -keyout "$ROOT/testes/recursos/tls-local-chave.pem" \
    -out "$ROOT/testes/recursos/tls-local-certificado.pem" \
    >/dev/null 2>&1
chmod 0600 "$ROOT/testes/recursos/tls-local-chave.pem"

REQUIRED=(
    bibs/bibf/correio.fé
    bibs/bibf/correio/agência.fé
    bibs/bibf/correio/imap.fé
    bibs/bibf/correio/LEIA-ME.md
    aplicativos/correio/LEIA-ME.md
    docs/ARQUITETURA-DO-ECOSSISTEMA.md
    testes/bibf/teste_correio_agência.fé
    testes/bibf/teste_correio_mime.fé
    testes/bibf/teste_correio_seguranca.fé
    testes/bibc/teste_correio_submissão_smtp.fé
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

echo "==> Validando módulos, comportamento e manual antes da troca"
grep -Fq 'versão = "0.5.0"' "$ROOT/bibs/bibf/correio.fé"
grep -Fq 'versão = "0.5.0"' "$ROOT/bibs/bibf/correio/imap.fé"
grep -Fq 'UTF8=ONLY' "$ROOT/bibs/bibf/correio/imap.fé"
grep -Fq 'Message-ID não aceita palavras MIME codificadas' \
    "$ROOT/bibs/bibf/correio.fé"
run_source_tests "$ROOT" 19995
validate_manual "$ROOT"

BACKUP="/var/backups/santafe-imap-unicode-$(date +%Y%m%d-%H%M%S)"
install -d -m 0700 "$BACKUP"

BACKUP_PATHS=(
    usr/local/share/santafé/1.0/bibf/correio.fé
    usr/local/share/santafé/1.0/bibf/correio/agência.fé
    usr/local/share/santafé/1.0/bibf/correio/imap.fé
    usr/local/share/santafé/1.0/bibf/correio/LEIA-ME.md
    var/www/santafé.dev.br/estático/manual/index.html
    home/${SUDO_USER:-rafael}/santafe-fonte/bibs/bibf/correio.fé
    home/${SUDO_USER:-rafael}/santafe-fonte/bibs/bibf/correio/agência.fé
    home/${SUDO_USER:-rafael}/santafe-fonte/bibs/bibf/correio/imap.fé
    home/${SUDO_USER:-rafael}/santafe-fonte/bibs/bibf/correio/LEIA-ME.md
    home/${SUDO_USER:-rafael}/santafe-fonte/aplicativos/correio/LEIA-ME.md
    home/${SUDO_USER:-rafael}/santafe-fonte/docs/ARQUITETURA-DO-ECOSSISTEMA.md
    home/${SUDO_USER:-rafael}/santafe-fonte/testes/bibf/teste_correio_agência.fé
    home/${SUDO_USER:-rafael}/santafe-fonte/testes/bibf/teste_correio_seguranca.fé
    home/${SUDO_USER:-rafael}/santafe-fonte/testes/bibc/teste_correio_submissão_smtp.fé
    home/${SUDO_USER:-rafael}/santafe-fonte/testes/integração/validar_imap.py
    home/${SUDO_USER:-rafael}/santafe-fonte/testes/integração/servidor_imap_memória.fé
    home/${SUDO_USER:-rafael}/santafe-fonte/site-sfdev/manual.html
    home/${SUDO_USER:-rafael}/santafe-fonte/site-sfdev/validar-manual.py
)

OPTIONAL_SOURCE_PATHS=(
    home/${SUDO_USER:-rafael}/santafe-fonte/testes/bibf/teste_correio_mime.fé
)
for relative in "${OPTIONAL_SOURCE_PATHS[@]}"; do
    if [[ -f "/$relative" ]]; then
        BACKUP_PATHS+=("$relative")
    else
        CREATED_PATHS+=("$relative")
    fi
done

for relative in "${BACKUP_PATHS[@]}"; do
    [[ -f "/$relative" ]] || {
        echo "Arquivo de produção ausente: /$relative" >&2
        exit 1
    }
done
tar -czf "$BACKUP/antes.tar.gz" -C / "${BACKUP_PATHS[@]}"

PUBLISHING=1
echo "==> Parando somente os consumidores postais"
stop_services

echo "==> Instalando o contrato Unicode 0.5.0"
install -o root -g root -m 0644 "$ROOT/bibs/bibf/correio.fé" \
    "$INSTALLED_BIBF/correio.fé"
install -o root -g root -m 0644 "$ROOT/bibs/bibf/correio/agência.fé" \
    "$INSTALLED_BIBF/correio/agência.fé"
install -o root -g root -m 0644 "$ROOT/bibs/bibf/correio/imap.fé" \
    "$INSTALLED_BIBF/correio/imap.fé"
install -o root -g root -m 0644 "$ROOT/bibs/bibf/correio/LEIA-ME.md" \
    "$INSTALLED_BIBF/correio/LEIA-ME.md"
install -o www-data -g www-data -m 0644 "$ROOT/site/manual.html" \
    "$INSTALLED_MANUAL"

echo "==> Reiniciando e validando Correio, Agência, IMAP e Carteiro"
start_services
wait_for_service correio-recebedor.service 25
wait_for_service correio-agencia.service 465
wait_for_service correio-agencia.service 587
wait_for_service correio-imap.service 993
wait_for_service carteiro.service 7100

/usr/local/bin/santafé -e \
    'local C=importe "correio"; local I=importe "correio.imap"; garanta(C.versão=="0.5.0"); garanta(I.versão=="0.5.0"); mostre("CORREIO_UNICODE_0_5_0_OK")'
run_source_tests "$ROOT" 19996
validate_manual "$ROOT"
validate_live_protocols

echo "==> Atualizando a árvore-fonte do servidor"
OWNER="${SUDO_USER:-rafael}"
GROUP="$(id -gn "$OWNER")"
SOURCE_FILES=(
    bibs/bibf/correio.fé
    bibs/bibf/correio/agência.fé
    bibs/bibf/correio/imap.fé
    bibs/bibf/correio/LEIA-ME.md
    aplicativos/correio/LEIA-ME.md
    docs/ARQUITETURA-DO-ECOSSISTEMA.md
    testes/bibf/teste_correio_agência.fé
    testes/bibf/teste_correio_mime.fé
    testes/bibf/teste_correio_seguranca.fé
    testes/bibc/teste_correio_submissão_smtp.fé
    testes/integração/validar_imap.py
    testes/integração/servidor_imap_memória.fé
)
for relative in "${SOURCE_FILES[@]}"; do
    install -d -o "$OWNER" -g "$GROUP" \
        "$(dirname "$SOURCE_ROOT/$relative")"
    install -o "$OWNER" -g "$GROUP" -m 0644 \
        "$ROOT/$relative" "$SOURCE_ROOT/$relative"
done
install -o "$OWNER" -g "$GROUP" -m 0644 "$ROOT/site/manual.html" \
    "$SOURCE_ROOT/site-sfdev/manual.html"
install -o "$OWNER" -g "$GROUP" -m 0644 "$ROOT/site/validar-manual.py" \
    "$SOURCE_ROOT/site-sfdev/validar-manual.py"

for service in "${SERVICES[@]}"; do
    systemctl is-active --quiet "$service"
done
systemctl is-active --quiet correio-envios.timer

PUBLISHING=0
trap - ERR
echo "Correio/IMAP Unicode 0.5.0 publicado e validado."
echo "Cópia de segurança: $BACKUP"
echo "UTF8=ONLY, ENABLE, APPEND UTF8 e cabeçalhos Unicode diretos: ativos."
