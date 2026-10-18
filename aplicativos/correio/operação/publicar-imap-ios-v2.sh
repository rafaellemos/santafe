#!/usr/bin/env bash

set -Eeuo pipefail

PACKAGE="/tmp/santafe-imap-ios-20260831-v2.tar.gz"
EXPECTED_HASH="4860ed501abbda6cf6b24e59068b42bccb8ca067036a9446d6301ac96c5dffa4"
SOURCE_ROOT="/home/${SUDO_USER:-rafael}/santafe-fonte"
SERVICE="correio-imap.service"
INSTALLED_BIBF="/usr/local/share/santafé/1.0/bibf"

WORK=""
ROOT=""
BACKUP=""
PUBLISHING=0
DEST_IMAP=""
SOURCE_IMAP=""
SOURCE_TEST_DIR=""

cleanup() {
    [[ -z "$WORK" || ! -d "$WORK" ]] || rm -rf -- "$WORK"
}

restore_previous() {
    local code="${1:-1}" line="${2:-unknown}" command="${3:-unknown}"
    trap - ERR
    set +e
    printf 'Falha na linha %s (código %s): %s\n' \
        "$line" "$code" "$command" >&2
    if [[ "$PUBLISHING" -eq 1 && -n "$BACKUP" && \
          -f "$BACKUP/antes.tar.gz" ]]; then
        echo "ERRO: atualização IMAP/iOS interrompida; restaurando a versão anterior."
        systemctl stop "$SERVICE" >/dev/null 2>&1 || true
        tar -xzf "$BACKUP/antes.tar.gz" -C /
        systemctl start "$SERVICE" >/dev/null 2>&1 || true
        echo "Versão anterior restaurada. Cópia de segurança: $BACKUP"
    fi
    exit "$code"
}

wait_for_imap() {
    local counter
    for ((counter=1; counter<=160; counter++)); do
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

trap cleanup EXIT
trap 'restore_previous "$?" "$LINENO" "$BASH_COMMAND"' ERR

[[ "$EUID" -eq 0 ]] || { echo "Execute com sudo." >&2; exit 1; }
echo "Publicador Correio IMAP 0.4.3 — contrato estrito do Mail para iOS"
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

WORK="$(mktemp -d /tmp/santafe-imap-ios-publicacao.XXXXXX)"
tar -xzf "$PACKAGE" -C "$WORK"
for file in imap.fe validar_imap.py servidor_imap_memoria.fe \
    certificado.pem chave.pem arquitetura.md correio-leia-me.md; do
    [[ -f "$WORK/$file" ]] || {
        echo "Arquivo ausente no pacote: $file" >&2
        exit 1
    }
done

ROOT="$WORK/raiz"
install -d "$ROOT/bibs/bibf/correio" \
    "$ROOT/testes/integração" "$ROOT/testes/recursos"
install -m 0644 "$WORK/imap.fe" "$ROOT/bibs/bibf/correio/imap.fé"
install -m 0644 "$WORK/validar_imap.py" \
    "$ROOT/testes/integração/validar_imap.py"
install -m 0644 "$WORK/servidor_imap_memoria.fe" \
    "$ROOT/testes/integração/servidor_imap_memória.fé"
install -m 0644 "$WORK/certificado.pem" \
    "$ROOT/testes/recursos/tls-local-certificado.pem"
install -m 0600 "$WORK/chave.pem" \
    "$ROOT/testes/recursos/tls-local-chave.pem"

DEST_IMAP="$(find "$INSTALLED_BIBF/correio" -maxdepth 1 \
    -type f -name 'imap.*' -print -quit)"
SOURCE_IMAP="$(find "$SOURCE_ROOT/bibs/bibf/correio" -maxdepth 1 \
    -type f -name 'imap.*' -print -quit)"
SOURCE_TEST_DIR="$(find "$SOURCE_ROOT/testes" -maxdepth 1 \
    -type d -name 'integra*' -print -quit)"
[[ -n "$DEST_IMAP" && -f "$DEST_IMAP" ]] || {
    echo "Módulo IMAP instalado não encontrado." >&2; exit 1;
}
[[ -n "$SOURCE_IMAP" && -f "$SOURCE_IMAP" ]] || {
    echo "Fonte IMAP do servidor não encontrada." >&2; exit 1;
}
[[ -n "$SOURCE_TEST_DIR" && -d "$SOURCE_TEST_DIR" ]] || {
    echo "Diretório de testes de integração não encontrado." >&2; exit 1;
}

echo "==> Validando o diálogo do iPhone antes da troca"
/usr/local/bin/santafec -p "$ROOT/bibs/bibf/correio/imap.fé"
/usr/local/bin/santafec -p \
    "$ROOT/testes/integração/servidor_imap_memória.fé"
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
    "$ROOT/testes/integração/validar_imap.py"
grep -F 'versão = "0.4.3"' "$ROOT/bibs/bibf/correio/imap.fé" >/dev/null
grep -F 'SASL-IR ID LIST-EXTENDED' \
    "$ROOT/bibs/bibf/correio/imap.fé" >/dev/null
(
    cd "$ROOT"
    PYTHONDONTWRITEBYTECODE=1 python3 testes/integração/validar_imap.py \
        --santafe /usr/local/bin/santafé --porta 19995
)

BACKUP="/var/backups/santafe-imap-ios-$(date +%Y%m%d-%H%M%S)"
install -d -m 0700 "$BACKUP"
MEMORY_TEST="$(find "$SOURCE_TEST_DIR" -maxdepth 1 \
    -type f -name 'servidor_imap_mem*' -print -quit)"
[[ -n "$MEMORY_TEST" && -f "$MEMORY_TEST" ]] || {
    echo "Ensaio IMAP em memória não encontrado." >&2; exit 1;
}
BACKUP_PATHS=(
    "${DEST_IMAP#/}"
    "${SOURCE_IMAP#/}"
    "${SOURCE_TEST_DIR#/}/validar_imap.py"
    "${MEMORY_TEST#/}"
    "${SOURCE_ROOT#/}/docs/ARQUITETURA-DO-ECOSSISTEMA.md"
    "${SOURCE_ROOT#/}/aplicativos/correio/LEIA-ME.md"
)
for path in "${BACKUP_PATHS[@]}"; do
    [[ -f "/$path" ]] || {
        echo "Arquivo de produção ausente: /$path" >&2
        exit 1
    }
done
tar -czf "$BACKUP/antes.tar.gz" -C / "${BACKUP_PATHS[@]}"

PUBLISHING=1
echo "==> Instalando somente o Correio IMAP 0.4.3"
systemctl stop "$SERVICE"
install -o root -g root -m 0644 \
    "$ROOT/bibs/bibf/correio/imap.fé" "$DEST_IMAP"
systemctl start "$SERVICE"
wait_for_imap

/usr/local/bin/santafé -e \
    'local I=importe "correio.imap"; garanta(I.versão=="0.4.3"); mostre("IMAP_0_4_3_OK")'
printf 'a1 CAPABILITY\r\na2 LOGOUT\r\n' > "$WORK/comandos-imap.txt"
if ! timeout 8 openssl s_client -connect 127.0.0.1:993 \
    -servername xn--santaf-gva.dev.br -quiet \
    < "$WORK/comandos-imap.txt" > "$WORK/respostas-imap.txt" 2>/dev/null; then
    :
fi
grep -Fq 'CAPABILITY IMAP4rev1 AUTH=PLAIN SASL-IR ID' \
    "$WORK/respostas-imap.txt"
grep -Fq 'UIDPLUS UNSELECT' "$WORK/respostas-imap.txt"

echo "==> Atualizando a árvore-fonte do servidor"
OWNER="${SUDO_USER:-rafael}"
GROUP="$(id -gn "$OWNER")"
install -o "$OWNER" -g "$GROUP" -m 0644 \
    "$ROOT/bibs/bibf/correio/imap.fé" "$SOURCE_IMAP"
install -o "$OWNER" -g "$GROUP" -m 0644 \
    "$ROOT/testes/integração/validar_imap.py" \
    "$SOURCE_TEST_DIR/validar_imap.py"
install -o "$OWNER" -g "$GROUP" -m 0644 \
    "$ROOT/testes/integração/servidor_imap_memória.fé" "$MEMORY_TEST"
install -o "$OWNER" -g "$GROUP" -m 0644 \
    "$WORK/arquitetura.md" \
    "$SOURCE_ROOT/docs/ARQUITETURA-DO-ECOSSISTEMA.md"
install -o "$OWNER" -g "$GROUP" -m 0644 \
    "$WORK/correio-leia-me.md" \
    "$SOURCE_ROOT/aplicativos/correio/LEIA-ME.md"

systemctl is-active --quiet "$SERVICE"
PUBLISHING=0
trap - ERR
echo "Correio IMAP 0.4.3 publicado e validado."
echo "Cópia de segurança: $BACKUP"
echo "O Mail do iPhone agora recebe capacidades pós-autenticação em US-ASCII."
