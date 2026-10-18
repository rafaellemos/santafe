#!/usr/bin/env bash

set -Eeuo pipefail

PACKAGE="/tmp/santafe-imap-20260831-v1.tar.gz"
EXPECTED_HASH="ae9bdb62e2f57b3137a4b0ecb1741b4bfaed3cb07d4d808fc54eb2de206c3c4c"
ENV_FILE="/etc/santafe/correio.env"
DEST_BIBF="/usr/local/share/santafé/1.0/bibf"
DEST_MAIL="/opt/correio"
DEST_MANUAL="/var/www/santafé.dev.br/estático/manual/index.html"
DEST_UNIT="/etc/systemd/system/correio-imap.service"
SERVER_SOURCE="/home/${SUDO_USER:-rafael}/santafe-fonte"
PREFLIGHT_UNIT="santafe-preflight-imap-v1.service"

WORK=""
ROOT=""
BACKUP=""
PUBLISHING=0
MIGRATION_APPLIED=0
IMAP_WAS_ENABLED=0
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
    if [[ -n "$WORK" && -d "$WORK" ]]; then rm -rf -- "$WORK"; fi
}

restore_previous() {
    local code="${1:-1}" line="${2:-unknown}" command="${3:-unknown}"
    trap - ERR
    set +e
    printf 'Falha na linha %s (código %s): %s\n' "$line" "$code" "$command" >&2
    stop_preflight
    cleanup_test_identity
    if [[ "$PUBLISHING" -eq 1 && -f "$BACKUP/before.tar.gz" ]]; then
        echo "ERRO: publicação IMAP interrompida; restaurando a versão anterior."
        systemctl disable --now correio-imap.service >/dev/null 2>&1 || true
        systemctl stop correio-agencia.service correio-envios.timer \
            correio-envios.service correio-recebedor.service carteiro.service \
            >/dev/null 2>&1 || true
        tar -xzf "$BACKUP/before.tar.gz" -C /
        while IFS= read -r absent; do
            [[ -z "$absent" ]] || rm -f -- "$absent"
        done < "$BACKUP/absent.txt"
        if [[ "$MIGRATION_APPLIED" -eq 1 ]]; then
            db_admin < "$ROOT/aplicativos/correio/banco/reverter-9-imap.sql" || true
        fi
        systemctl daemon-reload
        systemctl start correio-recebedor.service carteiro.service || true
        systemctl start correio-envios.timer || true
        systemctl enable --now correio-agencia.service || true
        if [[ "$IMAP_WAS_ENABLED" -eq 1 ]]; then
            systemctl enable --now correio-imap.service || true
        fi
        echo "Versão anterior restaurada. Cópia de segurança: $BACKUP"
    fi
    exit "$code"
}

append_env() {
    local key="$1" value="$2"
    grep -Eq "^${key}=" "$ENV_FILE" || printf '%s=%s\n' "$key" "$value" >> "$ENV_FILE"
}

wait_for_service() {
    local service="$1" attempts="${2:-120}" counter
    for ((counter=1; counter<=attempts; counter++)); do
        if systemctl is-active --quiet "$service"; then return 0; fi
        if systemctl is-failed --quiet "$service"; then break; fi
        sleep 0.25
    done
    systemctl status "$service" --no-pager -l >&2 || true
    journalctl -u "$service" -n 100 --no-pager -l >&2 || true
    return 1
}

trap cleanup EXIT
trap 'restore_previous "$?" "$LINENO" "$BASH_COMMAND"' ERR

[[ "$EUID" -eq 0 ]] || { echo "Execute com sudo." >&2; exit 1; }
echo "Publicador Correio IMAP v1.0 — TLS 993 e estrutura postal v9"
[[ -f "$PACKAGE" ]] || { echo "Pacote ausente: $PACKAGE" >&2; exit 1; }
[[ -r "$ENV_FILE" ]] || { echo "Ambiente postal indisponível." >&2; exit 1; }
ACTUAL_HASH="$(sha256sum "$PACKAGE" | awk '{print $1}')"
[[ "$ACTUAL_HASH" == "$EXPECTED_HASH" ]] || {
    echo "A soma do pacote não confere; nada foi alterado." >&2; exit 1;
}

for service in correio-recebedor.service carteiro.service \
               correio-envios.timer correio-agencia.service; do
    systemctl is-active --quiet "$service" || {
        echo "$service não está ativo; nada foi alterado." >&2; exit 1;
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
    echo "Nome do banco MariaDB inválido." >&2; exit 1;
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
DB_VERSION="$(db_admin -e "SELECT COALESCE(MAX(versao),0) FROM correio_migracoes WHERE componente='correio'")"
[[ "$DB_VERSION" == "8" || "$DB_VERSION" == "9" ]] || {
    echo "Estrutura postal inesperada: v$DB_VERSION; esperado v8 ou v9." >&2; exit 1;
}

WORK="$(mktemp -d /tmp/santafe-imap-publicacao.XXXXXX)"
chmod 0755 "$WORK"
ROOT="$WORK/source"
mkdir -p "$ROOT"
tar -xzf "$PACKAGE" -C "$ROOT"

REQUIRED=(
    bibs/bibf/correio.fé
    bibs/bibf/correio/imap.fé
    bibs/bibf/correio/mariadb.fé
    bibs/bibf/correio/LEIA-ME.md
    aplicativos/correio/imap.fé
    aplicativos/correio/fonte/correio/configuração.fé
    aplicativos/correio/operação/correio-imap.service
    aplicativos/correio/banco/migracao-9-imap.sql
    aplicativos/correio/banco/reverter-9-imap.sql
    testes/bibc/teste_correio_imap_mariadb.fé
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

echo "==> Validando fontes, protocolo em memória e manual"
for relative in \
    bibs/bibf/correio.fé \
    bibs/bibf/correio/imap.fé \
    bibs/bibf/correio/mariadb.fé \
    aplicativos/correio/imap.fé \
    aplicativos/correio/fonte/correio/configuração.fé \
    testes/bibc/teste_correio_imap_mariadb.fé \
    testes/integração/servidor_imap_memória.fé; do
    /usr/local/bin/santafec -p "$ROOT/$relative"
done
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

BACKUP="/var/backups/santafe-imap-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP"
: > "$BACKUP/absent.txt"
TARGETS=(
    "$DEST_BIBF/correio.fé"
    "$DEST_BIBF/correio/imap.fé"
    "$DEST_BIBF/correio/mariadb.fé"
    "$DEST_BIBF/correio/LEIA-ME.md"
    "$DEST_MAIL/imap.fé"
    "$DEST_MAIL/fonte/correio/configuração.fé"
    "$DEST_MAIL/LEIA-ME.md"
    "$DEST_UNIT"
    "$ENV_FILE"
    "$DEST_MANUAL"
)
EXISTING=()
for target in "${TARGETS[@]}"; do
    if [[ -e "$target" ]]; then EXISTING+=("$target")
    else printf '%s\n' "$target" >> "$BACKUP/absent.txt"; fi
done
tar -czf "$BACKUP/before.tar.gz" "${EXISTING[@]}"
if systemctl is-enabled --quiet correio-imap.service 2>/dev/null; then
    IMAP_WAS_ENABLED=1
fi

PUBLISHING=1
echo "==> Parando somente os consumidores postais"
systemctl stop correio-imap.service >/dev/null 2>&1 || true
systemctl stop correio-agencia.service
systemctl stop correio-envios.timer
systemctl stop correio-envios.service >/dev/null 2>&1 || true
systemctl stop correio-recebedor.service carteiro.service

if [[ "$DB_VERSION" == "8" ]]; then
    echo "==> Aplicando a estrutura postal v9"
    db_admin < "$ROOT/aplicativos/correio/banco/migracao-9-imap.sql"
    MIGRATION_APPLIED=1
else
    echo "==> Estrutura postal v9 já presente; conferindo idempotência"
    db_admin < "$ROOT/aplicativos/correio/banco/migracao-9-imap.sql"
fi
[[ "$(db_admin -e "SELECT COALESCE(MAX(versao),0) FROM correio_migracoes WHERE componente='correio'")" == "9" ]]

TEST_USER="imap-preflight-$(date +%s)-$$"
TEST_PASSWORD="$(openssl rand -hex 24)"
TEST_HASH="$(SANTAFE_TEST_PASSWORD="$TEST_PASSWORD" \
    LUA_PATH="$ROOT/bibs/bibf/?.fé;$ROOT/bibs/bibf/?/?.fé;$DEST_BIBF/?.fé;$DEST_BIBF/?/?.fé;;" \
    LUA_CPATH="/usr/local/lib/santafé/1.0/bibc/?.so;;" \
    /usr/local/bin/santafé -e 'local S=importe "segredo"; local R=importe "rede"; local ok,f=S.protejaSenhaAssíncrono(so.obterVariável("SANTAFE_TEST_PASSWORD"),função(r,falha) garanta(r,falha); mostre(r); R.pareLaço() fim); garanta(ok,f); R.laço()')"
[[ -n "$TEST_HASH" ]]
db_admin -e "INSERT INTO usuarios (nome,usuario,email,senha_hash,papel,estado) VALUES ('Ensaio IMAP','${TEST_USER}','${TEST_USER}@santafé.dev.br','${TEST_HASH}','usuário','ativo')"

echo "==> Testando o IMAP transitório em 127.0.0.1:19993"
PREFLIGHT_PULSE="/var/lib/santafé/correio/preflight-imap-$$.pulso"
systemd-run --unit="$PREFLIGHT_UNIT" --uid=correio --gid=correio \
    --working-directory="$ROOT" \
    --property="EnvironmentFile=$ENV_FILE" \
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
wait_for_service "$PREFLIGHT_UNIT"
READY=0
for attempt in {1..120}; do
    if ss -ltn | grep -Eq '127\.0\.0\.1:19993([[:space:]]|$)'; then READY=1; break; fi
    sleep 0.25
done
[[ "$READY" -eq 1 ]]
python3 "$ROOT/testes/integração/validar_imap_servidor.py" \
    --host 127.0.0.1 --porta 19993 \
    --usuario "$TEST_USER@xn--santaf-gva.dev.br" --senha "$TEST_PASSWORD"
stop_preflight

echo "==> Instalando o Correio 0.4.0 e o acesso IMAP"
mkdir -p "$DEST_BIBF/correio" "$DEST_MAIL/fonte/correio"
install -o root -g root -m 0644 "$ROOT/bibs/bibf/correio.fé" \
    "$DEST_BIBF/correio.fé"
for name in imap.fé mariadb.fé LEIA-ME.md; do
    install -o root -g root -m 0644 "$ROOT/bibs/bibf/correio/$name" \
        "$DEST_BIBF/correio/$name"
done
install -o root -g correio -m 0640 "$ROOT/aplicativos/correio/imap.fé" \
    "$DEST_MAIL/imap.fé"
install -o root -g correio -m 0640 \
    "$ROOT/aplicativos/correio/fonte/correio/configuração.fé" \
    "$DEST_MAIL/fonte/correio/configuração.fé"
install -o root -g correio -m 0640 "$ROOT/aplicativos/correio/LEIA-ME.md" \
    "$DEST_MAIL/LEIA-ME.md"
install -o root -g root -m 0644 \
    "$ROOT/aplicativos/correio/operação/correio-imap.service" "$DEST_UNIT"
install -o root -g www-data -m 0644 "$ROOT/manual.html" "$DEST_MANUAL"

append_env CORREIO_IMAP_ENDERECO 0.0.0.0
append_env CORREIO_IMAP_PORTA 993
append_env CORREIO_IMAP_NOME "$IMAP_NAME"
append_env CORREIO_IMAP_CERTIFICADO "$IMAP_CERT"
append_env CORREIO_IMAP_CHAVE "$IMAP_KEY"
append_env CORREIO_IMAP_TEMPO_LIMITE 1800000
append_env CORREIO_IMAP_LIMITE_LINHA 16384
append_env CORREIO_IMAP_LIMITE_COMANDOS 10000
append_env CORREIO_IMAP_LIMITE_CONEXOES 500
append_env CORREIO_IMAP_LIMITE_CONEXOES_POR_ENDERECO 10
append_env CORREIO_IMAP_LIMITE_NOVAS_POR_MINUTO 60
append_env CORREIO_IMAP_LIMITE_AUTENTICACAO 5

echo "==> Reiniciando e validando os serviços postais"
systemctl daemon-reload
systemctl start correio-recebedor.service carteiro.service
systemctl start correio-envios.timer
systemctl enable --now correio-agencia.service
systemctl enable --now correio-imap.service
for service in correio-recebedor.service carteiro.service \
               correio-envios.timer correio-agencia.service correio-imap.service; do
    wait_for_service "$service"
done

READY=0
for attempt in {1..240}; do
    if ss -ltn | grep -Eq ':993([[:space:]]|$)'; then READY=1; break; fi
    if systemctl is-failed --quiet correio-imap.service; then break; fi
    sleep 0.25
done
[[ "$READY" -eq 1 ]]
python3 "$ROOT/testes/integração/validar_imap_servidor.py" \
    --host 127.0.0.1 --porta 993 \
    --usuario "$TEST_USER@xn--santaf-gva.dev.br" --senha "$TEST_PASSWORD"
cleanup_test_identity

HTTP_READY=0
for attempt in {1..120}; do
    if curl -fsS --max-time 2 -o "$WORK/carteiro-state.json" \
        http://127.0.0.1:7100/carteiro/estado 2>/dev/null &&
       grep -Fq '"estado":"pronto"' "$WORK/carteiro-state.json"; then
        HTTP_READY=1; break
    fi
    sleep 0.25
done
[[ "$HTTP_READY" -eq 1 ]]
timeout 5 bash -c \
    'exec 3<>/dev/tcp/127.0.0.1/25; IFS= read -r line <&3; [[ "$line" == 220* ]]'
grep -Fq 'id="correio-imap-servidor"' "$DEST_MANUAL"
grep -Fq 'Leitura num cliente postal:' "$DEST_MANUAL"
runuser -u correio -- env \
    LUA_PATH="$DEST_BIBF/?.fé;$DEST_BIBF/?/?.fé;;" \
    LUA_CPATH="/usr/local/lib/santafé/1.0/bibc/?.so;;" \
    /usr/local/bin/santafé -e \
    'local C=importe "correio"; local I=importe "correio.imap"; garanta(C.versão=="0.4.0"); garanta(I.versão=="0.1.0"); garanta(tipo(I.servidor)=="função"); mostre("IMAP_INSTALADO_OK")' \
    > "$WORK/installed-module.txt"
grep -Fxq 'IMAP_INSTALADO_OK' "$WORK/installed-module.txt"

echo "==> Atualizando a árvore-fonte do servidor"
if [[ -d "$SERVER_SOURCE" ]]; then
    OWNER="${SUDO_USER:-rafael}"
    GROUP="$(id -gn "$OWNER")"
    SOURCE_FILES=(
        Makefile
        bibs/bibf/correio.fé
        bibs/bibf/correio/imap.fé
        bibs/bibf/correio/mariadb.fé
        bibs/bibf/correio/LEIA-ME.md
        aplicativos/correio/imap.fé
        aplicativos/correio/fonte/correio/configuração.fé
        aplicativos/correio/operação/correio.env.exemplo
        aplicativos/correio/operação/correio-imap.service
        aplicativos/correio/banco/estrutura.sql
        aplicativos/correio/banco/migracao-9-imap.sql
        aplicativos/correio/banco/reverter-9-imap.sql
        aplicativos/correio/LEIA-ME.md
        docs/ARQUITETURA-DO-ECOSSISTEMA.md
        testes/bibc/teste_correio_imap_mariadb.fé
        testes/integração/servidor_imap_memória.fé
        testes/integração/validar_imap.py
        testes/integração/validar_imap_servidor.py
        testes/integracao/testar_correio_mariadb.sh
    )
    for relative in "${SOURCE_FILES[@]}"; do
        source_file="$ROOT/$relative"
        destination="$SERVER_SOURCE/$relative"
        mkdir -p "$(dirname "$destination")"
        mode=0644
        [[ "$relative" == *.sh || "$relative" == *.py ]] && mode=0755
        install -o "$OWNER" -g "$GROUP" -m "$mode" "$source_file" "$destination"
    done
    if [[ -d "$SERVER_SOURCE/site-sfdev" ]]; then
        install -o "$OWNER" -g "$GROUP" -m 0644 "$ROOT/manual.html" \
            "$SERVER_SOURCE/site-sfdev/manual.html"
        install -o "$OWNER" -g "$GROUP" -m 0644 "$ROOT/validar-manual.py" \
            "$SERVER_SOURCE/site-sfdev/validar-manual.py"
    fi
fi

PUBLISHING=0
echo "Correio IMAP publicado e validado. Cópia de segurança: $BACKUP"
echo "Entrada: 993/TLS; usuário: endereço postal completo; senha: a do portal."
echo "SMTP permanece em 25 (servidores), 465 e 587 (clientes autenticados)."
