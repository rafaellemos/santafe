#!/usr/bin/env bash

set -Eeuo pipefail

PACKAGE="/tmp/santafe-imap-idle-20260831-v1.tar.gz"
EXPECTED_HASH="6ba3f390c94073ebb0b1ed9bc4e6533903f75c31716bd17b5e5f76cb343e6a71"
ENV_FILE="/etc/santafe/correio.env"
DEST_BIBF="/usr/local/share/santafé/1.0/bibf"
DEST_MAIL="/opt/correio"
DEST_MANUAL="/var/www/santafé.dev.br/estático/manual/index.html"
SERVER_SOURCE="/home/${SUDO_USER:-rafael}/santafe-fonte"

WORK=""
ROOT=""
BACKUP=""
PUBLISHING=0

cleanup() {
    if [[ -n "$WORK" && -d "$WORK" ]]; then rm -rf -- "$WORK"; fi
}

restore_previous() {
    local code="${1:-1}" line="${2:-unknown}" command="${3:-unknown}"
    trap - ERR
    set +e
    printf 'Falha na linha %s (código %s): %s\n' "$line" "$code" "$command" >&2
    if [[ "$PUBLISHING" -eq 1 && -f "$BACKUP/before.tar.gz" ]]; then
        echo "ERRO: atualização do IDLE interrompida; restaurando o IMAP anterior."
        systemctl stop correio-imap.service >/dev/null 2>&1 || true
        tar -xzf "$BACKUP/before.tar.gz" -C /
        systemctl start correio-imap.service || true
        echo "Versão anterior restaurada. Cópia de segurança: $BACKUP"
    fi
    exit "$code"
}

append_env() {
    local key="$1" value="$2"
    grep -Eq "^${key}=" "$ENV_FILE" || printf '%s=%s\n' "$key" "$value" >> "$ENV_FILE"
}

wait_for_imap() {
    local counter
    for ((counter=1; counter<=160; counter++)); do
        if systemctl is-active --quiet correio-imap.service &&
           ss -ltn | grep -Eq ':993([[:space:]]|$)'; then
            return 0
        fi
        if systemctl is-failed --quiet correio-imap.service; then break; fi
        sleep 0.25
    done
    systemctl status correio-imap.service --no-pager -l >&2 || true
    journalctl -u correio-imap.service -n 100 --no-pager -l >&2 || true
    return 1
}

trap cleanup EXIT
trap 'restore_previous "$?" "$LINENO" "$BASH_COMMAND"' ERR

[[ "$EUID" -eq 0 ]] || { echo "Execute com sudo." >&2; exit 1; }
echo "Publicador Correio IMAP IDLE v1.0 — avisos ativos da caixa selecionada"
[[ -f "$PACKAGE" ]] || { echo "Pacote ausente: $PACKAGE" >&2; exit 1; }
[[ -r "$ENV_FILE" ]] || { echo "Ambiente postal indisponível." >&2; exit 1; }
ACTUAL_HASH="$(sha256sum "$PACKAGE" | awk '{print $1}')"
[[ "$ACTUAL_HASH" == "$EXPECTED_HASH" ]] || {
    echo "A soma do pacote não confere; nada foi alterado." >&2; exit 1;
}
systemctl is-active --quiet correio-imap.service || {
    echo "correio-imap.service não está ativo; nada foi alterado." >&2; exit 1;
}

WORK="$(mktemp -d /tmp/santafe-imap-idle-publicacao.XXXXXX)"
chmod 0755 "$WORK"
ROOT="$WORK/source"
mkdir -p "$ROOT"
tar -xzf "$PACKAGE" -C "$ROOT"

REQUIRED=(
    bibs/bibf/correio/imap.fé
    bibs/bibf/correio/LEIA-ME.md
    aplicativos/correio/imap.fé
    aplicativos/correio/fonte/correio/configuração.fé
    aplicativos/correio/operação/correio.env.exemplo
    aplicativos/correio/LEIA-ME.md
    docs/ARQUITETURA-DO-ECOSSISTEMA.md
    testes/integração/servidor_imap_memória.fé
    testes/integração/validar_imap.py
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

echo "==> Validando o IDLE ativo, as fontes e o manual"
for relative in \
    bibs/bibf/correio/imap.fé \
    aplicativos/correio/imap.fé \
    aplicativos/correio/fonte/correio/configuração.fé \
    testes/integração/servidor_imap_memória.fé; do
    /usr/local/bin/santafec -p "$ROOT/$relative"
done
(
    cd "$ROOT"
    LUA_PATH="$ROOT/bibs/bibf/?.fé;$ROOT/bibs/bibf/?/?.fé;$DEST_BIBF/?.fé;$DEST_BIBF/?/?.fé;;" \
    LUA_CPATH="/usr/local/lib/santafé/1.0/bibc/?.so;;" \
    python3 testes/integração/validar_imap.py \
        --santafe /usr/local/bin/santafé --porta 19992
)
python3 "$ROOT/validar-manual.py" "$ROOT/manual.html" \
    --compilador /usr/local/bin/santafec

BACKUP="/var/backups/santafe-imap-idle-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP"
TARGETS=(
    "$DEST_BIBF/correio/imap.fé"
    "$DEST_BIBF/correio/LEIA-ME.md"
    "$DEST_MAIL/imap.fé"
    "$DEST_MAIL/fonte/correio/configuração.fé"
    "$DEST_MAIL/LEIA-ME.md"
    "$ENV_FILE"
    "$DEST_MANUAL"
)
tar -czf "$BACKUP/before.tar.gz" "${TARGETS[@]}"

PUBLISHING=1
echo "==> Reiniciando somente o acesso IMAP"
systemctl stop correio-imap.service
install -o root -g root -m 0644 "$ROOT/bibs/bibf/correio/imap.fé" \
    "$DEST_BIBF/correio/imap.fé"
install -o root -g root -m 0644 "$ROOT/bibs/bibf/correio/LEIA-ME.md" \
    "$DEST_BIBF/correio/LEIA-ME.md"
install -o root -g correio -m 0640 "$ROOT/aplicativos/correio/imap.fé" \
    "$DEST_MAIL/imap.fé"
install -o root -g correio -m 0640 \
    "$ROOT/aplicativos/correio/fonte/correio/configuração.fé" \
    "$DEST_MAIL/fonte/correio/configuração.fé"
install -o root -g correio -m 0640 "$ROOT/aplicativos/correio/LEIA-ME.md" \
    "$DEST_MAIL/LEIA-ME.md"
install -o root -g www-data -m 0644 "$ROOT/manual.html" "$DEST_MANUAL"
append_env CORREIO_IMAP_INTERVALO_OCIOSO 15000
systemctl start correio-imap.service
wait_for_imap

CAPABILITIES="$(printf 'a1 CAPABILITY\r\na2 LOGOUT\r\n' | \
    timeout 10 openssl s_client -quiet -connect 127.0.0.1:993 \
        -servername xn--santaf-gva.dev.br 2>/dev/null)"
grep -Fq 'CAPABILITY IMAP4rev1' <<<"$CAPABILITIES"
grep -Fq ' IDLE ' <<<"$CAPABILITIES"
runuser -u correio -- env \
    LUA_PATH="$DEST_BIBF/?.fé;$DEST_BIBF/?/?.fé;;" \
    LUA_CPATH="/usr/local/lib/santafé/1.0/bibc/?.so;;" \
    /usr/local/bin/santafé -e \
    'local I=importe "correio.imap"; garanta(I.versão=="0.2.0"); mostre("IMAP_IDLE_INSTALADO_OK")' \
    > "$WORK/installed-module.txt"
grep -Fxq 'IMAP_IDLE_INSTALADO_OK' "$WORK/installed-module.txt"
grep -Fq 'Durante IDLE' "$DEST_MANUAL"

echo "==> Atualizando a árvore-fonte do servidor"
if [[ -d "$SERVER_SOURCE" ]]; then
    OWNER="${SUDO_USER:-rafael}"
    GROUP="$(id -gn "$OWNER")"
    SOURCE_FILES=(
        bibs/bibf/correio/imap.fé
        bibs/bibf/correio/LEIA-ME.md
        aplicativos/correio/imap.fé
        aplicativos/correio/fonte/correio/configuração.fé
        aplicativos/correio/operação/correio.env.exemplo
        aplicativos/correio/LEIA-ME.md
        docs/ARQUITETURA-DO-ECOSSISTEMA.md
        testes/integração/servidor_imap_memória.fé
        testes/integração/validar_imap.py
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
echo "IMAP IDLE ativo publicado e validado. Cópia de segurança: $BACKUP"
echo "Chegadas, remoções e sinalizadores agora são anunciados sem NOOP."
