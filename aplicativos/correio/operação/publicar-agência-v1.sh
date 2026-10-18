#!/usr/bin/env bash

set -Eeuo pipefail

PACKAGE="/tmp/santafe-agencia-20260831-v4.tar.gz"
EXPECTED_HASH="4ed1745b4bc6f32b3f4f9fe906d0ef800b0925463fe98e799cc7c56d0ccf69b1"
ENV_FILE="/etc/santafe/correio.env"
DEST_BIBF="/usr/local/share/santafé/1.0/bibf"
DEST_MAIL="/opt/correio"
DEST_MANUAL="/var/www/santafé.dev.br/estático/manual/index.html"
DEST_UNIT="/etc/systemd/system/correio-agencia.service"
SERVER_SOURCE="/home/${SUDO_USER:-rafael}/santafe-fonte"

WORK=""
ROOT=""
BACKUP=""
PUBLISHING=0
PREFLIGHT_UNIT="santafe-preflight-agencia-v1.service"
PREFLIGHT_PULSE=""
TEST_USER=""
AGENCY_WAS_ENABLED=0

db_admin() {
    mariadb --protocol=socket --batch --raw --skip-column-names \
        "$SANTAFE_MARIADB_BANCO" "$@"
}

cleanup_test_identity() {
    if [[ -z "${TEST_USER:-}" || -z "${SANTAFE_MARIADB_BANCO:-}" ]]; then
        return
    fi
    db_admin -e "DELETE c FROM correio_caixas c JOIN usuarios u ON u.id=c.usuario_id WHERE u.usuario='${TEST_USER}'; DELETE FROM usuarios WHERE usuario='${TEST_USER}';" \
        >/dev/null 2>&1 || true
}

stop_preflight() {
    systemctl stop "$PREFLIGHT_UNIT" >/dev/null 2>&1 || true
    systemctl reset-failed "$PREFLIGHT_UNIT" >/dev/null 2>&1 || true
    if [[ -n "$PREFLIGHT_PULSE" ]]; then
        rm -f -- "$PREFLIGHT_PULSE"
    fi
}

cleanup() {
    stop_preflight
    cleanup_test_identity
    if [[ -n "$WORK" && -d "$WORK" ]]; then
        rm -rf -- "$WORK"
    fi
}

restore_previous() {
    local code="${1:-1}"
    local line="${2:-unknown}"
    local command="${3:-unknown}"
    trap - ERR
    set +e
    printf 'Falha na linha %s (código %s): %s\n' \
        "$line" "$code" "$command" >&2
    stop_preflight
    cleanup_test_identity
    if [[ "$PUBLISHING" -eq 1 && -f "$BACKUP/before.tar.gz" ]]; then
        echo "ERRO: publicação interrompida; restaurando a versão anterior."
        systemctl disable --now correio-agencia.service >/dev/null 2>&1 || true
        systemctl stop correio-envios.timer correio-envios.service \
            correio-recebedor.service carteiro.service >/dev/null 2>&1 || true
        tar -xzf "$BACKUP/before.tar.gz" -C /
        while IFS= read -r absent; do
            [[ -n "$absent" ]] && rm -f -- "$absent"
        done < "$BACKUP/absent.txt"
        systemctl daemon-reload
        systemctl start correio-recebedor.service carteiro.service || true
        systemctl start correio-envios.timer || true
        if [[ "$AGENCY_WAS_ENABLED" -eq 1 ]]; then
            systemctl enable --now correio-agencia.service || true
        fi
        echo "Versão anterior restaurada. Cópia de segurança: $BACKUP"
    fi
    exit "$code"
}

append_env() {
    local key="$1"
    local value="$2"
    if grep -Eq "^${key}=" "$ENV_FILE"; then
        return
    fi
    printf '%s=%s\n' "$key" "$value" >> "$ENV_FILE"
}

wait_for_service() {
    local service="$1"
    local attempts="${2:-120}"
    local counter
    for ((counter=1; counter<=attempts; counter++)); do
        if systemctl is-active --quiet "$service"; then
            return 0
        fi
        if systemctl is-failed --quiet "$service"; then
            break
        fi
        sleep 0.25
    done
    systemctl status "$service" --no-pager -l >&2 || true
    journalctl -u "$service" -n 100 --no-pager -l >&2 || true
    return 1
}

trap cleanup EXIT
trap 'restore_previous "$?" "$LINENO" "$BASH_COMMAND"' ERR

[[ "$EUID" -eq 0 ]] || { echo "Execute com sudo." >&2; exit 1; }
echo "Publicador Correio Agência v4.0 — capacidade e portas 465/587 validadas"
[[ -f "$PACKAGE" ]] || { echo "Pacote ausente: $PACKAGE" >&2; exit 1; }
[[ -r "$ENV_FILE" ]] || { echo "Ambiente postal indisponível." >&2; exit 1; }
ACTUAL_HASH="$(sha256sum "$PACKAGE" | awk '{print $1}')"
[[ "$ACTUAL_HASH" == "$EXPECTED_HASH" ]] || {
    echo "A soma do pacote não confere; nada foi alterado." >&2
    exit 1
}

for service in correio-recebedor.service carteiro.service correio-envios.timer; do
    systemctl is-active --quiet "$service" || {
        echo "$service não está ativo; nada foi alterado." >&2
        exit 1
    }
done

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
AGENCY_NAME="${CORREIO_AGENCIA_NOME:-${CORREIO_RECEBEDOR_NOME:-xn--santaf-gva.dev.br}}"
AGENCY_CERT="${CORREIO_AGENCIA_CERTIFICADO:-${CORREIO_RECEBEDOR_CERTIFICADO:-}}"
AGENCY_KEY="${CORREIO_AGENCIA_CHAVE:-${CORREIO_RECEBEDOR_CHAVE:-}}"
[[ -n "$AGENCY_CERT" && -r "$AGENCY_CERT" ]] || {
    echo "Certificado SMTP da Agência ausente ou ilegível." >&2; exit 1;
}
[[ -n "$AGENCY_KEY" && -r "$AGENCY_KEY" ]] || {
    echo "Chave SMTP da Agência ausente ou ilegível." >&2; exit 1;
}
db_admin -e "SELECT 1" >/dev/null

WORK="$(mktemp -d /tmp/santafe-agencia-publicacao.XXXXXX)"
chmod 0755 "$WORK"
ROOT="$WORK/source"
mkdir -p "$ROOT"
tar -xzf "$PACKAGE" -C "$ROOT"

REQUIRED=(
    bibs/bibf/correio.fé
    bibs/bibf/correio/agência.fé
    bibs/bibf/correio/mariadb.fé
    bibs/bibf/correio/LEIA-ME.md
    aplicativos/correio/agência.fé
    aplicativos/correio/fonte/correio/configuração.fé
    aplicativos/correio/operação/correio-agencia.service
    aplicativos/correio/LEIA-ME.md
    testes/bibf/teste_correio_agência.fé
    testes/bibc/teste_correio_submissão_smtp.fé
    testes/bibc/teste_correio_agência_mariadb.fé
    testes/integração/validar_agência_smtp.py
    manual.html
    validar-manual.py
)
for relative in "${REQUIRED[@]}"; do
    [[ -f "$ROOT/$relative" ]] || {
        echo "Arquivo ausente no pacote: $relative" >&2; exit 1;
    }
done

echo "==> Validando fontes, protocolo, identidade e manual"
for relative in \
    bibs/bibf/correio.fé \
    bibs/bibf/correio/agência.fé \
    bibs/bibf/correio/mariadb.fé \
    aplicativos/correio/agência.fé \
    aplicativos/correio/fonte/correio/configuração.fé \
    testes/bibf/teste_correio_agência.fé \
    testes/bibc/teste_correio_submissão_smtp.fé \
    testes/bibc/teste_correio_agência_mariadb.fé; do
    /usr/local/bin/santafec -p "$ROOT/$relative"
done
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
    "$ROOT/testes/integração/validar_agência_smtp.py"
(
    cd "$ROOT"
    export LUA_PATH="$ROOT/bibs/bibf/?.fé;$ROOT/bibs/bibf/?/?.fé;$DEST_BIBF/?.fé;$DEST_BIBF/?/?.fé;;"
    export LUA_CPATH="/usr/local/lib/santafé/1.0/bibc/?.so;;"
    /usr/local/bin/santafé testes/bibf/teste_correio_agência.fé
    timeout 30 /usr/local/bin/santafé \
        testes/bibc/teste_correio_submissão_smtp.fé
)
python3 "$ROOT/validar-manual.py" "$ROOT/manual.html" \
    --compilador /usr/local/bin/santafec

TEST_USER="agencia-preflight-$(date +%s)-$$"
(
    cd "$ROOT"
    runuser -u correio -- env \
        SANTAFE_MARIADB_HOST="${SANTAFE_MARIADB_HOST:-127.0.0.1}" \
        SANTAFE_MARIADB_PORTA="${SANTAFE_MARIADB_PORTA:-3306}" \
        SANTAFE_MARIADB_USUARIO="$SANTAFE_MARIADB_USUARIO" \
        SANTAFE_MARIADB_SENHA="$SANTAFE_MARIADB_SENHA" \
        SANTAFE_MARIADB_BANCO="$SANTAFE_MARIADB_BANCO" \
        SANTAFE_TESTE_USUARIO="$TEST_USER" \
        LUA_PATH="$ROOT/bibs/bibf/?.fé;$ROOT/bibs/bibf/?/?.fé;$DEST_BIBF/?.fé;$DEST_BIBF/?/?.fé;;" \
        LUA_CPATH="/usr/local/lib/santafé/1.0/bibc/?.so;;" \
        /usr/local/bin/santafé testes/bibc/teste_correio_agência_mariadb.fé
)
[[ "$(db_admin -e "SELECT COUNT(*) FROM usuarios WHERE usuario='${TEST_USER}'")" == "0" ]]
TEST_USER=""

echo "==> Testando a Agência transitória em 127.0.0.1"
PREFLIGHT_PULSE="/var/lib/santafé/correio/preflight-agencia-$$.pulso"
systemd-run --unit="$PREFLIGHT_UNIT" --uid=correio --gid=correio \
    --working-directory="$ROOT" \
    --property="EnvironmentFile=$ENV_FILE" \
    --property="AmbientCapabilities=CAP_NET_BIND_SERVICE" \
    --property="CapabilityBoundingSet=CAP_NET_BIND_SERVICE" \
    /usr/bin/env \
    "CORREIO_RAIZ=$ROOT/aplicativos/correio" \
    "CORREIO_AGENCIA_ENDERECO=127.0.0.1" \
    "CORREIO_AGENCIA_PORTA_STARTTLS=587" \
    "CORREIO_AGENCIA_PORTA_TLS=465" \
    "CORREIO_AGENCIA_NOME=$AGENCY_NAME" \
    "CORREIO_AGENCIA_CERTIFICADO=$AGENCY_CERT" \
    "CORREIO_AGENCIA_CHAVE=$AGENCY_KEY" \
    "CORREIO_PULSO_ARQUIVO=$PREFLIGHT_PULSE" \
    "LUA_PATH=$ROOT/bibs/bibf/?.fé;$ROOT/bibs/bibf/?/?.fé;$DEST_BIBF/?.fé;$DEST_BIBF/?/?.fé;;" \
    "LUA_CPATH=/usr/local/lib/santafé/1.0/bibc/?.so;;" \
    /usr/local/bin/santafé "$ROOT/aplicativos/correio/agência.fé"
wait_for_service "$PREFLIGHT_UNIT"
READY=0
for attempt in {1..80}; do
    ss -ltn > "$WORK/preflight-ports.txt"
    if grep -Fq '127.0.0.1:465' "$WORK/preflight-ports.txt" &&
       grep -Fq '127.0.0.1:587' "$WORK/preflight-ports.txt"; then
        READY=1
        break
    fi
    sleep 0.25
done
if [[ "$READY" -ne 1 ]]; then
    systemctl status "$PREFLIGHT_UNIT" --no-pager -l >&2 || true
    journalctl -u "$PREFLIGHT_UNIT" -n 100 --no-pager -l >&2 || true
    false
fi
python3 "$ROOT/testes/integração/validar_agência_smtp.py" \
    --host 127.0.0.1 --porta-starttls 587 --porta-tls 465 \
    --nome "$AGENCY_NAME"
stop_preflight

BACKUP="/var/backups/santafe-agencia-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP"
: > "$BACKUP/absent.txt"
TARGETS=(
    "$DEST_BIBF/correio.fé"
    "$DEST_BIBF/correio/agência.fé"
    "$DEST_BIBF/correio/mariadb.fé"
    "$DEST_BIBF/correio/LEIA-ME.md"
    "$DEST_MAIL/agência.fé"
    "$DEST_MAIL/fonte/correio/configuração.fé"
    "$DEST_MAIL/LEIA-ME.md"
    "$DEST_UNIT"
    "$ENV_FILE"
    "$DEST_MANUAL"
)
EXISTING=()
for target in "${TARGETS[@]}"; do
    if [[ -e "$target" ]]; then
        EXISTING+=("$target")
    else
        printf '%s\n' "$target" >> "$BACKUP/absent.txt"
    fi
done
tar -czf "$BACKUP/before.tar.gz" "${EXISTING[@]}"
if systemctl is-enabled --quiet correio-agencia.service 2>/dev/null; then
    AGENCY_WAS_ENABLED=1
fi

PUBLISHING=1
echo "==> Parando somente os consumidores postais"
systemctl stop correio-agencia.service >/dev/null 2>&1 || true
systemctl stop correio-envios.timer
systemctl stop correio-envios.service >/dev/null 2>&1 || true
systemctl stop correio-recebedor.service carteiro.service

echo "==> Instalando a Agência e o contrato SMTP atualizado"
mkdir -p "$DEST_BIBF/correio" "$DEST_MAIL/fonte/correio"
install -o root -g root -m 0644 "$ROOT/bibs/bibf/correio.fé" \
    "$DEST_BIBF/correio.fé"
for name in agência.fé mariadb.fé LEIA-ME.md; do
    install -o root -g root -m 0644 "$ROOT/bibs/bibf/correio/$name" \
        "$DEST_BIBF/correio/$name"
done
install -o root -g correio -m 0640 "$ROOT/aplicativos/correio/agência.fé" \
    "$DEST_MAIL/agência.fé"
install -o root -g correio -m 0640 \
    "$ROOT/aplicativos/correio/fonte/correio/configuração.fé" \
    "$DEST_MAIL/fonte/correio/configuração.fé"
install -o root -g correio -m 0640 "$ROOT/aplicativos/correio/LEIA-ME.md" \
    "$DEST_MAIL/LEIA-ME.md"
install -o root -g root -m 0644 \
    "$ROOT/aplicativos/correio/operação/correio-agencia.service" \
    "$DEST_UNIT"
install -o root -g www-data -m 0644 "$ROOT/manual.html" "$DEST_MANUAL"

append_env CORREIO_AGENCIA_ENDERECO 0.0.0.0
append_env CORREIO_AGENCIA_PORTA_STARTTLS 587
append_env CORREIO_AGENCIA_PORTA_TLS 465
append_env CORREIO_AGENCIA_NOME "$AGENCY_NAME"
append_env CORREIO_AGENCIA_CERTIFICADO "$AGENCY_CERT"
append_env CORREIO_AGENCIA_CHAVE "$AGENCY_KEY"
append_env CORREIO_AGENCIA_LIMITE_CONEXOES 500
append_env CORREIO_AGENCIA_LIMITE_CONEXOES_POR_ENDERECO 10
append_env CORREIO_AGENCIA_LIMITE_NOVAS_POR_MINUTO 30
append_env CORREIO_AGENCIA_LIMITE_AUTENTICACAO 3

echo "==> Reiniciando e validando os serviços postais"
systemctl daemon-reload
systemctl start correio-recebedor.service carteiro.service
systemctl start correio-envios.timer
systemctl enable --now correio-agencia.service
wait_for_service correio-recebedor.service
wait_for_service carteiro.service
wait_for_service correio-envios.timer
wait_for_service correio-agencia.service

SMTP_READY=0
for attempt in {1..240}; do
    ss -ltn > "$WORK/production-ports.txt"
    if grep -Eq ':465([[:space:]]|$)' "$WORK/production-ports.txt" &&
       grep -Eq ':587([[:space:]]|$)' "$WORK/production-ports.txt"; then
        SMTP_READY=1
        break
    fi
    if systemctl is-failed --quiet correio-agencia.service; then
        break
    fi
    sleep 0.25
done
if [[ "$SMTP_READY" -ne 1 ]]; then
    systemctl status correio-agencia.service --no-pager -l >&2 || true
    journalctl -u correio-agencia.service -n 100 --no-pager -l >&2 || true
    false
fi

HTTP_READY=0
for attempt in {1..120}; do
    if curl -fsS --max-time 2 -o "$WORK/carteiro-state.json" \
        http://127.0.0.1:7100/carteiro/estado 2>/dev/null &&
       grep -Fq '"estado":"pronto"' "$WORK/carteiro-state.json"; then
        HTTP_READY=1
        break
    fi
    sleep 0.25
done
[[ "$HTTP_READY" -eq 1 ]]
timeout 5 bash -c \
    'exec 3<>/dev/tcp/127.0.0.1/25; IFS= read -r line <&3; [[ "$line" == 220* ]]'
python3 "$ROOT/testes/integração/validar_agência_smtp.py" \
    --host 127.0.0.1 --porta-starttls 587 --porta-tls 465 \
    --nome "$AGENCY_NAME"
grep -Fq 'id="correio-agencia-nova"' "$DEST_MANUAL"
grep -Fq 'Configuração de um cliente:' "$DEST_MANUAL"
runuser -u correio -- env \
    LUA_PATH="$DEST_BIBF/?.fé;$DEST_BIBF/?/?.fé;;" \
    LUA_CPATH="/usr/local/lib/santafé/1.0/bibc/?.so;;" \
    /usr/local/bin/santafé -e \
    'local C=importe "correio"; local A=importe "correio.agência"; garanta(C.versão=="0.4.0"); garanta(tipo(A.nova)=="função"); mostre("AGENCIA_INSTALADA_OK")' \
    > "$WORK/installed-module.txt"
grep -Fxq 'AGENCIA_INSTALADA_OK' "$WORK/installed-module.txt"

echo "==> Atualizando a árvore-fonte do servidor"
if [[ -d "$SERVER_SOURCE" ]]; then
    OWNER="${SUDO_USER:-rafael}"
    GROUP="$(id -gn "$OWNER")"
    SOURCE_FILES=(
        bibs/bibf/correio.fé
        bibs/bibf/correio/agência.fé
        bibs/bibf/correio/mariadb.fé
        bibs/bibf/correio/LEIA-ME.md
        aplicativos/correio/agência.fé
        aplicativos/correio/fonte/correio/configuração.fé
        aplicativos/correio/operação/correio.env.exemplo
        aplicativos/correio/operação/correio-agencia.service
        aplicativos/correio/LEIA-ME.md
        docs/ARQUITETURA-DO-ECOSSISTEMA.md
        testes/bibf/teste_correio_agência.fé
        testes/bibc/teste_correio_submissão_smtp.fé
        testes/bibc/teste_correio_agência_mariadb.fé
        testes/recursos/correio-base-mariadb.sql
        testes/integração/validar_agência_smtp.py
    )
    for relative in "${SOURCE_FILES[@]}"; do
        source_file="$ROOT/$relative"
        destination="$SERVER_SOURCE/$relative"
        mkdir -p "$(dirname "$destination")"
        mode=0644
        [[ "$relative" == *.sh || "$relative" == *.py ]] && mode=0755
        install -o "$OWNER" -g "$GROUP" -m "$mode" \
            "$source_file" "$destination"
    done
    if [[ -d "$SERVER_SOURCE/site-sfdev" ]]; then
        install -o "$OWNER" -g "$GROUP" -m 0644 "$ROOT/manual.html" \
            "$SERVER_SOURCE/site-sfdev/manual.html"
        install -o "$OWNER" -g "$GROUP" -m 0644 "$ROOT/validar-manual.py" \
            "$SERVER_SOURCE/site-sfdev/validar-manual.py"
    fi
    install -o "$OWNER" -g "$GROUP" -m 0755 "$0" \
        "$SERVER_SOURCE/aplicativos/correio/operação/publicar-agência-v1.sh"
fi

PUBLISHING=0
echo "Correio Agência publicado e validado. Cópia de segurança: $BACKUP"
echo "Submissão autenticada: 465/TLS preferida e 587/STARTTLS obrigatório."
echo "A porta 25 continua exclusiva da troca entre servidores."
