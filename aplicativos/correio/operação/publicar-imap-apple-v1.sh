#!/usr/bin/env bash

set -Eeuo pipefail

PACKAGE="/tmp/santafe-imap-apple-20260831-v2.tar.gz"
EXPECTED_HASH="4b8bf09a81fcfc17eb0deade83c8417fc2896318ebc6f2e49aedd90fec834231"
ENV_FILE="/etc/santafe/correio.env"
DEST_BIBF="/usr/local/share/santafé/1.0/bibf"
DEST_MAIL="/opt/correio"
DEST_MANUAL="/var/www/santafé.dev.br/estático/manual/index.html"
SERVER_SOURCE="/home/${SUDO_USER:-rafael}/santafe-fonte"
PREFLIGHT_UNIT="santafe-preflight-imap-apple.service"

WORK=""
ROOT=""
BACKUP=""
PUBLISHING=0
TEST_USER=""
TEST_PASSWORD=""
PREFLIGHT_PULSE=""

db_admin() {
    mariadb --protocol=socket --batch --raw --skip-column-names \
        "$SANTAFE_MARIADB_BANCO" "$@"
}

stop_preflight() {
    systemctl stop "$PREFLIGHT_UNIT" >/dev/null 2>&1 || true
    systemctl reset-failed "$PREFLIGHT_UNIT" >/dev/null 2>&1 || true
    [[ -z "$PREFLIGHT_PULSE" ]] || rm -f -- "$PREFLIGHT_PULSE"
}

cleanup_test_identity() {
    if [[ -z "$TEST_USER" || -z "${SANTAFE_MARIADB_BANCO:-}" ]]; then
        return
    fi
    db_admin -e "DELETE c FROM correio_caixas c JOIN usuarios u ON u.id=c.usuario_id WHERE u.usuario='${TEST_USER}'; DELETE FROM usuarios WHERE usuario='${TEST_USER}';" \
        >/dev/null 2>&1 || true
    TEST_USER=""
    TEST_PASSWORD=""
}

cleanup() {
    stop_preflight
    cleanup_test_identity
    [[ -z "$WORK" || ! -d "$WORK" ]] || rm -rf -- "$WORK"
}

restore_previous() {
    local code="${1:-1}" line="${2:-unknown}" command="${3:-unknown}"
    trap - ERR
    set +e
    printf 'Falha na linha %s (código %s): %s\n' \
        "$line" "$code" "$command" >&2
    stop_preflight
    cleanup_test_identity
    if [[ "$PUBLISHING" -eq 1 && -f "$BACKUP/before.tar.gz" ]]; then
        echo "ERRO: correção Apple Mail interrompida; restaurando o IMAP anterior."
        systemctl stop correio-imap.service >/dev/null 2>&1 || true
        tar -xzf "$BACKUP/before.tar.gz" -C /
        systemctl start correio-imap.service || true
        echo "Versão anterior restaurada. Cópia de segurança: $BACKUP"
    fi
    exit "$code"
}

wait_for_imap() {
    local service="$1" port="$2" counter
    for ((counter=1; counter<=160; counter++)); do
        if systemctl is-active --quiet "$service" &&
           ss -ltn | grep -E ":${port}([[:space:]]|$)" >/dev/null; then
            return 0
        fi
        if systemctl is-failed --quiet "$service"; then break; fi
        sleep 0.25
    done
    systemctl status "$service" --no-pager -l >&2 || true
    journalctl -u "$service" -n 100 --no-pager -l >&2 || true
    return 1
}

validate_server() {
    local port="$1"
    SANTAFE_IMAP_TEST_PASSWORD="$TEST_PASSWORD" \
        PYTHONDONTWRITEBYTECODE=1 \
        python3 "$ROOT/testes/integração/validar_imap_servidor.py" \
            --host 127.0.0.1 --porta "$port" \
            --usuario "$TEST_USER@xn--santaf-gva.dev.br"
}

trap cleanup EXIT
trap 'restore_previous "$?" "$LINENO" "$BASH_COMMAND"' ERR

[[ "$EUID" -eq 0 ]] || { echo "Execute com sudo." >&2; exit 1; }
echo "Publicador Correio IMAP 0.4.0 v2 — compatibilidade estrita com Apple Mail"
[[ -f "$PACKAGE" ]] || { echo "Pacote ausente: $PACKAGE" >&2; exit 1; }
[[ -r "$ENV_FILE" ]] || { echo "Ambiente postal indisponível." >&2; exit 1; }
ACTUAL_HASH="$(sha256sum "$PACKAGE" | awk '{print $1}')"
[[ "$ACTUAL_HASH" == "$EXPECTED_HASH" ]] || {
    echo "A soma do pacote não confere; nada foi alterado." >&2
    exit 1
}
systemctl is-active --quiet correio-imap.service || {
    echo "correio-imap.service não está ativo; nada foi alterado." >&2
    exit 1
}

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
: "${SANTAFE_MARIADB_BANCO:?banco MariaDB ausente}"
: "${SANTAFE_MARIADB_USUARIO:?usuário MariaDB ausente}"
: "${SANTAFE_MARIADB_SENHA:?senha MariaDB ausente}"
[[ "$SANTAFE_MARIADB_BANCO" =~ ^[A-Za-z0-9_]+$ ]] || {
    echo "Nome do banco MariaDB inválido." >&2
    exit 1
}
IMAP_NAME="${CORREIO_IMAP_NOME:-${CORREIO_AGENCIA_NOME:-${CORREIO_RECEBEDOR_NOME:-xn--santaf-gva.dev.br}}}"
IMAP_CERT="${CORREIO_IMAP_CERTIFICADO:-${CORREIO_AGENCIA_CERTIFICADO:-${CORREIO_RECEBEDOR_CERTIFICADO:-}}}"
IMAP_KEY="${CORREIO_IMAP_CHAVE:-${CORREIO_AGENCIA_CHAVE:-${CORREIO_RECEBEDOR_CHAVE:-}}}"
[[ -n "$IMAP_CERT" && -r "$IMAP_CERT" ]] || {
    echo "Certificado IMAP ausente ou ilegível." >&2; exit 1;
}
[[ -n "$IMAP_KEY" && -r "$IMAP_KEY" ]] || {
    echo "Chave IMAP ausente ou ilegível." >&2; exit 1;
}
db_admin -e "SELECT 1" >/dev/null
[[ "$(db_admin -e "SELECT COALESCE(MAX(versao),0) FROM correio_migracoes WHERE componente='correio'")" == "9" ]] || {
    echo "A estrutura postal v9 não está aplicada; nada foi alterado." >&2
    exit 1
}

WORK="$(mktemp -d /tmp/santafe-imap-apple-publicacao.XXXXXX)"
ROOT="$WORK/source"
mkdir -p "$ROOT"
tar -xzf "$PACKAGE" -C "$ROOT"
chmod 0755 "$WORK" "$ROOT"

REQUIRED=(
    bibs/bibf/correio/imap.fé
    aplicativos/correio/imap.fé
    aplicativos/correio/LEIA-ME.md
    aplicativos/correio/fonte/correio/configuração.fé
    docs/ARQUITETURA-DO-ECOSSISTEMA.md
    testes/integração/servidor_imap_memória.fé
    testes/integração/validar_imap.py
    testes/integração/validar_imap_servidor.py
    testes/recursos/tls-local-certificado.pem
    testes/recursos/tls-local-chave.pem
    manual.html
    validar-manual.py
)
for relative in "${REQUIRED[@]}"; do
    [[ -f "$ROOT/$relative" ]] || {
        echo "Arquivo ausente no pacote: $relative" >&2; exit 1;
    }
done

echo "==> Validando fontes, descoberta de caixas, corpos e manual"
/usr/local/bin/santafec -p "$ROOT/bibs/bibf/correio/imap.fé"
/usr/local/bin/santafec -p "$ROOT/testes/integração/servidor_imap_memória.fé"
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
    "$ROOT/testes/integração/validar_imap.py" \
    "$ROOT/testes/integração/validar_imap_servidor.py"
(
    cd "$ROOT"
    LUA_PATH="$ROOT/bibs/bibf/?.fé;$ROOT/bibs/bibf/?/?.fé;$DEST_BIBF/?.fé;$DEST_BIBF/?/?.fé;;" \
    LUA_CPATH="/usr/local/lib/santafé/1.0/bibc/?.so;;" \
    python3 testes/integração/validar_imap.py \
        --santafe /usr/local/bin/santafé --porta 19992
)
python3 "$ROOT/validar-manual.py" "$ROOT/manual.html" \
    --compilador /usr/local/bin/santafec

TEST_USER="imap-apple-$(date +%s)-$$"
TEST_PASSWORD="$(openssl rand -hex 24)"
TEST_HASH="$(SANTAFE_TEST_PASSWORD="$TEST_PASSWORD" \
    LUA_PATH="$ROOT/bibs/bibf/?.fé;$ROOT/bibs/bibf/?/?.fé;$DEST_BIBF/?.fé;$DEST_BIBF/?/?.fé;;" \
    LUA_CPATH="/usr/local/lib/santafé/1.0/bibc/?.so;;" \
    /usr/local/bin/santafé -e 'local S=importe "segredo"; local R=importe "rede"; local ok,f=S.protejaSenhaAssíncrono(so.obterVariável("SANTAFE_TEST_PASSWORD"),função(r,falha) garanta(r,falha); mostre(r); R.pareLaço() fim); garanta(ok,f); R.laço()')"
[[ -n "$TEST_HASH" ]]
db_admin -e "INSERT INTO usuarios (nome,usuario,email,senha_hash,papel,estado) VALUES ('Ensaio IMAP Apple','${TEST_USER}','${TEST_USER}@santafé.dev.br','${TEST_HASH}','usuário','ativo')"

echo "==> Testando o IMAP corrigido em 127.0.0.1:19993"
PREFLIGHT_PULSE="/var/lib/santafé/correio/preflight-imap-apple-$$.pulso"
systemd-run --unit="$PREFLIGHT_UNIT" --uid=correio --gid=correio \
    --working-directory="$ROOT" --property="EnvironmentFile=$ENV_FILE" \
    /usr/bin/env \
    "CORREIO_RAIZ=$ROOT/aplicativos/correio" \
    "CORREIO_IMAP_ENDERECO=127.0.0.1" \
    "CORREIO_IMAP_PORTA=19993" \
    "CORREIO_IMAP_NOME=$IMAP_NAME" \
    "CORREIO_IMAP_CERTIFICADO=$IMAP_CERT" \
    "CORREIO_IMAP_CHAVE=$IMAP_KEY" \
    "CORREIO_PULSO_ARQUIVO=$PREFLIGHT_PULSE" \
    "LUA_PATH=$ROOT/bibs/bibf/?.fé;$ROOT/bibs/bibf/?/?.fé;$DEST_BIBF/?.fé;$DEST_BIBF/?/?.fé;;" \
    "LUA_CPATH=/usr/local/lib/santafé/1.0/bibc/?.so;;" \
    /usr/local/bin/santafé "$ROOT/aplicativos/correio/imap.fé"
wait_for_imap "$PREFLIGHT_UNIT" 19993
validate_server 19993
stop_preflight

BACKUP="/var/backups/santafe-imap-apple-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP"
TARGETS=(
    "$DEST_BIBF/correio/imap.fé"
    "$DEST_MAIL/LEIA-ME.md"
    "$DEST_MANUAL"
)
tar -czf "$BACKUP/before.tar.gz" "${TARGETS[@]}"

PUBLISHING=1
echo "==> Reiniciando somente o acesso IMAP"
systemctl stop correio-imap.service
install -o root -g root -m 0644 "$ROOT/bibs/bibf/correio/imap.fé" \
    "$DEST_BIBF/correio/imap.fé"
install -o root -g correio -m 0640 "$ROOT/aplicativos/correio/LEIA-ME.md" \
    "$DEST_MAIL/LEIA-ME.md"
install -o root -g www-data -m 0644 "$ROOT/manual.html" "$DEST_MANUAL"
systemctl start correio-imap.service
wait_for_imap correio-imap.service 993
validate_server 993

runuser -u correio -- env \
    LUA_PATH="$DEST_BIBF/?.fé;$DEST_BIBF/?/?.fé;;" \
    LUA_CPATH="/usr/local/lib/santafé/1.0/bibc/?.so;;" \
    /usr/local/bin/santafé -e \
    'local I=importe "correio.imap"; garanta(I.versão=="0.4.0"); mostre("IMAP_APPLE_INSTALADO_OK")' \
    > "$WORK/installed-module.txt"
grep -Fx 'IMAP_APPLE_INSTALADO_OK' "$WORK/installed-module.txt" >/dev/null
cleanup_test_identity

echo "==> Atualizando a árvore-fonte do servidor"
if [[ -d "$SERVER_SOURCE" ]]; then
    OWNER="${SUDO_USER:-rafael}"
    GROUP="$(id -gn "$OWNER")"
    SOURCE_FILES=(
        bibs/bibf/correio/imap.fé
        aplicativos/correio/LEIA-ME.md
        docs/ARQUITETURA-DO-ECOSSISTEMA.md
        testes/integração/servidor_imap_memória.fé
        testes/integração/validar_imap.py
        testes/integração/validar_imap_servidor.py
    )
    for relative in "${SOURCE_FILES[@]}"; do
        destination="$SERVER_SOURCE/$relative"
        mkdir -p "$(dirname "$destination")"
        mode=0644
        [[ "$relative" == *.py ]] && mode=0755
        install -o "$OWNER" -g "$GROUP" -m "$mode" \
            "$ROOT/$relative" "$destination"
    done
    if [[ -d "$SERVER_SOURCE/site-sfdev" ]]; then
        install -o "$OWNER" -g "$GROUP" -m 0644 "$ROOT/manual.html" \
            "$SERVER_SOURCE/site-sfdev/manual.html"
        install -o "$OWNER" -g "$GROUP" -m 0644 "$ROOT/validar-manual.py" \
            "$SERVER_SOURCE/site-sfdev/validar-manual.py"
    fi
fi

PUBLISHING=0
echo "IMAP 0.4.0 publicado e validado. Cópia de segurança: $BACKUP"
echo "Apple Mail: descoberta estrita de caixas e leitura de corpos corrigidas."
