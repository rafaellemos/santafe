#!/usr/bin/env bash
set -Eeuo pipefail

PACKAGE="/tmp/santafe-carteiro-configurador-20260831.tar.gz"
CHECKSUM="${PACKAGE}.sha256"
PACKAGE_ROOT="santafe-carteiro-configurador-20260831"
TEMP_DIR=""
BACKUP_DIR=""
CHANGED=0
HAD_CONFIGURATOR=0
SERVER_SOURCE="/home/${SUDO_USER:-rafael}/santafe-fonte"
CARTEIRO_ROOT="/opt/carteiro"
PUBLIC_CSS="/var/www/santafé.dev.br/carteiro/estático/css/carteiro.css"
INSTALLED_BIBF="/usr/local/share/santafé/1.0/bibf"
INSTALLED_BIBC="/usr/local/lib/santafé/1.0/bibc"

cleanup() {
    if [[ -n "$TEMP_DIR" && -d "$TEMP_DIR" ]]; then
        rm -rf -- "$TEMP_DIR"
    fi
}

rollback() {
    local code="${1:-1}"
    local line="${2:-unknown}"
    local command="${3:-unknown}"
    trap - ERR
    set +e
    echo "Falha na linha $line (código $code): $command" >&2
    if [[ "$CHANGED" -eq 1 && -f "$BACKUP_DIR/before.tar.gz" ]]; then
        echo "ERRO: atualização interrompida; restaurando o Carteiro anterior."
        systemctl stop carteiro.service
        tar -xzf "$BACKUP_DIR/before.tar.gz" -C /
        if [[ "$HAD_CONFIGURATOR" -eq 0 ]]; then
            rm -f "$CARTEIRO_ROOT/fonte/carteiro/configurador.fé"
        fi
        systemctl start carteiro.service || true
        echo "Versão anterior restaurada. Cópia de segurança: $BACKUP_DIR"
    fi
    exit "$code"
}

trap cleanup EXIT
trap 'rollback "$?" "$LINENO" "$BASH_COMMAND"' ERR

[[ "$EUID" -eq 0 ]] || { echo "Execute com sudo." >&2; exit 1; }
[[ -f "$PACKAGE" && -f "$CHECKSUM" ]] || {
    echo "Pacote ou soma ausente em /tmp." >&2; exit 1;
}

(cd /tmp && sha256sum -c "$(basename "$CHECKSUM")")
TEMP_DIR="$(mktemp -d /tmp/santafe-carteiro-configurador.XXXXXX)"
tar -xzf "$PACKAGE" -C "$TEMP_DIR"
ROOT="$TEMP_DIR/$PACKAGE_ROOT"

FILES=(
    "aplicativos/carteiro/fonte/carteiro/configurador.fé"
    "aplicativos/carteiro/fonte/carteiro/aplicação.fé"
    "aplicativos/carteiro/fonte/carteiro/páginas.fé"
    "aplicativos/carteiro/fonte/carteiro/web.fé"
    "aplicativos/carteiro/estático/css/carteiro.css"
    "aplicativos/carteiro/LEIA-ME.md"
    "aplicativos/carteiro/operação/publicar-configurador.sh"
    "testes/bibf/teste_carteiro_configurador.fé"
    "testes/bibc/teste_carteiro_http.fé"
)
for relative in "${FILES[@]}"; do
    [[ -f "$ROOT/$relative" ]] || {
        echo "Arquivo ausente no pacote: $relative" >&2; exit 1;
    }
done

echo "==> Validando fontes e perfil antes da troca"
for relative in \
    "aplicativos/carteiro/fonte/carteiro/configurador.fé" \
    "aplicativos/carteiro/fonte/carteiro/aplicação.fé" \
    "aplicativos/carteiro/fonte/carteiro/páginas.fé" \
    "testes/bibf/teste_carteiro_configurador.fé" \
    "testes/bibc/teste_carteiro_http.fé"; do
    /usr/local/bin/santafec -p "$ROOT/$relative"
done

env \
    LUA_PATH="$ROOT/aplicativos/carteiro/fonte/?.fé;$INSTALLED_BIBF/?.fé;$INSTALLED_BIBF/?/?.fé;;" \
    LUA_CPATH="$INSTALLED_BIBC/?.so;;" \
    /usr/local/bin/santafé "$ROOT/testes/bibf/teste_carteiro_configurador.fé"
env \
    LUA_PATH="$ROOT/aplicativos/carteiro/fonte/?.fé;$INSTALLED_BIBF/?.fé;$INSTALLED_BIBF/?/?.fé;;" \
    LUA_CPATH="$INSTALLED_BIBC/?.so;;" \
    /usr/local/bin/santafé "$ROOT/testes/bibc/teste_carteiro_http.fé"

BACKUP_DIR="/var/backups/santafe-carteiro-configurador-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"
if [[ -f "$CARTEIRO_ROOT/fonte/carteiro/configurador.fé" ]]; then
    HAD_CONFIGURATOR=1
fi
BACKUP_FILES=(
    "opt/carteiro/fonte/carteiro/aplicação.fé" \
    "opt/carteiro/fonte/carteiro/páginas.fé" \
    "opt/carteiro/LEIA-ME.md" \
    "var/www/santafé.dev.br/carteiro/estático/css/carteiro.css"
)
if [[ "$HAD_CONFIGURATOR" -eq 1 ]]; then
    BACKUP_FILES+=("opt/carteiro/fonte/carteiro/configurador.fé")
fi
tar -czf "$BACKUP_DIR/before.tar.gz" -C / "${BACKUP_FILES[@]}"
CHANGED=1

echo "==> Instalando o configurador autenticado"
systemctl stop carteiro.service
install -o root -g carteiro -m 0640 \
    "$ROOT/aplicativos/carteiro/fonte/carteiro/configurador.fé" \
    "$CARTEIRO_ROOT/fonte/carteiro/configurador.fé"
for name in aplicação.fé páginas.fé; do
    install -o root -g carteiro -m 0640 \
        "$ROOT/aplicativos/carteiro/fonte/carteiro/$name" \
        "$CARTEIRO_ROOT/fonte/carteiro/$name"
done
install -o root -g carteiro -m 0640 \
    "$ROOT/aplicativos/carteiro/LEIA-ME.md" "$CARTEIRO_ROOT/LEIA-ME.md"
install -o root -g www-data -m 0644 \
    "$ROOT/aplicativos/carteiro/estático/css/carteiro.css" "$PUBLIC_CSS"
systemctl start carteiro.service

echo "==> Validando o serviço e o caminho protegido"
READY=0
for _ in $(seq 1 120); do
    if systemctl is-active --quiet carteiro.service &&
       curl -fsS --max-time 2 -o "$TEMP_DIR/state.json" \
           http://127.0.0.1:7100/carteiro/estado 2>/dev/null &&
       grep -Fq '"estado":"pronto"' "$TEMP_DIR/state.json"; then
        READY=1
        break
    fi
    sleep 0.25
done
if [[ "$READY" -ne 1 ]]; then
    systemctl status carteiro.service --no-pager -l >&2 || true
    journalctl -u carteiro.service -n 60 --no-pager -l >&2 || true
    false
fi

curl -sS --max-time 4 -D "$TEMP_DIR/config.headers" -o /dev/null \
    http://127.0.0.1:7100/carteiro/configurar
grep -Eq '^HTTP/1\.[01] 303' "$TEMP_DIR/config.headers"
grep -Fq 'location: /entrar?destino=/carteiro/' \
    <(tr '[:upper:]' '[:lower:]' < "$TEMP_DIR/config.headers")
grep -Fq 'carteiro.configurador' "$CARTEIRO_ROOT/fonte/carteiro/aplicação.fé"
grep -Fq 'Baixar perfil Apple' "$CARTEIRO_ROOT/fonte/carteiro/páginas.fé"
grep -Fq 'application/x-apple-aspen-config' \
    "$CARTEIRO_ROOT/fonte/carteiro/aplicação.fé"

echo "==> Atualizando a árvore-fonte do servidor"
if [[ -d "$SERVER_SOURCE" ]]; then
    OWNER="${SUDO_USER:-rafael}"
    GROUP="$(id -gn "$OWNER")"
    for relative in "${FILES[@]}"; do
        destination="$SERVER_SOURCE/$relative"
        mkdir -p "$(dirname "$destination")"
        install -o "$OWNER" -g "$GROUP" -m 0644 "$ROOT/$relative" "$destination"
    done
fi

CHANGED=0
trap - ERR
echo "Configurador do Carteiro publicado e validado. Cópia de segurança: $BACKUP_DIR"
echo "Perfil Apple: IMAP 993/TLS, SMTP 465/TLS e nenhuma senha incorporada."
