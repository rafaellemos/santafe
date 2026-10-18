#!/usr/bin/env bash

set -Eeuo pipefail

PACKAGE="/tmp/santafe-imap-corpo-20260831.tar.gz"
EXPECTED_HASH="e2aeabab65cf4e61e137e829e2c0215d9e83787af935c2a7064b2a3a069c2f17"
SOURCE_ROOT="/home/${SUDO_USER:-rafael}/santafe-fonte"
SERVICE="correio-imap.service"

WORK=""
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
    if [[ "$PUBLISHING" -eq 1 && -n "$BACKUP" ]]; then
        echo "ERRO: correção IMAP interrompida; restaurando a versão anterior."
        systemctl stop "$SERVICE" >/dev/null 2>&1 || true
        [[ ! -f "$BACKUP/imap-instalado.fe" ]] || \
            install -m 0644 "$BACKUP/imap-instalado.fe" "$DEST_IMAP"
        [[ ! -f "$BACKUP/imap-fonte.fe" ]] || \
            install -o "${SUDO_USER:-rafael}" -g "${SUDO_USER:-rafael}" \
                -m 0644 "$BACKUP/imap-fonte.fe" "$SOURCE_IMAP"
        [[ ! -f "$BACKUP/arquitetura.md" ]] || \
            install -o "${SUDO_USER:-rafael}" -g "${SUDO_USER:-rafael}" \
                -m 0644 "$BACKUP/arquitetura.md" \
                "$SOURCE_ROOT/docs/ARQUITETURA-DO-ECOSSISTEMA.md"
        systemctl start "$SERVICE" >/dev/null 2>&1 || true
        echo "Versão anterior restaurada. Cópia de segurança: $BACKUP"
    fi
    exit "$code"
}

wait_for_imap() {
    local counter
    for ((counter=1; counter<=120; counter++)); do
        if systemctl is-active --quiet "$SERVICE" &&
           [[ -n "$(ss -ltnH 'sport = :993')" ]]; then
            return 0
        fi
        if systemctl is-failed --quiet "$SERVICE"; then break; fi
        sleep 0.25
    done
    systemctl status "$SERVICE" --no-pager -l >&2 || true
    journalctl -u "$SERVICE" -n 100 --no-pager -l >&2 || true
    return 1
}

trap cleanup EXIT
trap 'restore_previous "$?" "$LINENO" "$BASH_COMMAND"' ERR

[[ "$EUID" -eq 0 ]] || { echo "Execute com sudo." >&2; exit 1; }
echo "Publicador Correio IMAP 0.4.1 — associação obrigatória de UID no FETCH"
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

WORK="$(mktemp -d /tmp/santafe-imap-corpo-publicacao.XXXXXX)"
tar -xzf "$PACKAGE" -C "$WORK"
for file in imap.fe validar_imap.py validar_imap_servidor.py \
    servidor_imap_memoria.fe arquitetura.md; do
    [[ -f "$WORK/$file" ]] || { echo "Arquivo ausente: $file" >&2; exit 1; }
done

DEST_ROOT="$(find /usr/local/share -maxdepth 1 -type d -name 'santaf*' -print -quit)"
[[ -n "$DEST_ROOT" ]] || { echo "Raiz Santafé instalada não encontrada." >&2; exit 1; }
DEST_IMAP="$(find "$DEST_ROOT/1.0/bibf/correio" -maxdepth 1 -type f -name 'imap.*' -print -quit)"
SOURCE_IMAP="$(find "$SOURCE_ROOT/bibs/bibf/correio" -maxdepth 1 -type f -name 'imap.*' -print -quit)"
SOURCE_TEST_DIR="$(find "$SOURCE_ROOT/testes" -maxdepth 1 -type d -name 'integra*' -print -quit)"
[[ -n "$DEST_IMAP" && -f "$DEST_IMAP" ]] || {
    echo "Módulo IMAP instalado não encontrado." >&2; exit 1;
}
[[ -n "$SOURCE_IMAP" && -f "$SOURCE_IMAP" ]] || {
    echo "Fonte IMAP do servidor não encontrada." >&2; exit 1;
}
[[ -n "$SOURCE_TEST_DIR" && -d "$SOURCE_TEST_DIR" ]] || {
    echo "Diretório de testes de integração não encontrado." >&2; exit 1;
}

/usr/local/bin/santafec -p "$WORK/imap.fe"
PYTHONDONTWRITEBYTECODE=1 python3 -c \
    'from pathlib import Path; [compile(Path(p).read_text(), p, "exec") for p in __import__("sys").argv[1:]]' \
    "$WORK/validar_imap.py" "$WORK/validar_imap_servidor.py"
grep -F 'versão = "0.4.1"' "$WORK/imap.fe" >/dev/null
grep -F 'tabela.insira(atributos, 1, "UID")' "$WORK/imap.fe" >/dev/null

BACKUP="/var/backups/santafe-imap-corpo-$(date +%Y%m%d-%H%M%S)"
install -d -m 0700 "$BACKUP"
cp -a "$DEST_IMAP" "$BACKUP/imap-instalado.fe"
cp -a "$SOURCE_IMAP" "$BACKUP/imap-fonte.fe"
[[ ! -f "$SOURCE_ROOT/docs/ARQUITETURA-DO-ECOSSISTEMA.md" ]] || \
    cp -a "$SOURCE_ROOT/docs/ARQUITETURA-DO-ECOSSISTEMA.md" \
        "$BACKUP/arquitetura.md"

PUBLISHING=1
echo "==> Instalando somente a correção do corpo IMAP"
systemctl stop "$SERVICE"
install -m 0644 "$WORK/imap.fe" "$DEST_IMAP"
install -o "${SUDO_USER:-rafael}" -g "${SUDO_USER:-rafael}" -m 0644 \
    "$WORK/imap.fe" "$SOURCE_IMAP"
install -o "${SUDO_USER:-rafael}" -g "${SUDO_USER:-rafael}" -m 0644 \
    "$WORK/validar_imap.py" "$SOURCE_TEST_DIR/validar_imap.py"
install -o "${SUDO_USER:-rafael}" -g "${SUDO_USER:-rafael}" -m 0644 \
    "$WORK/validar_imap_servidor.py" "$SOURCE_TEST_DIR/validar_imap_servidor.py"
MEMORY_TEST="$(find "$SOURCE_TEST_DIR" -maxdepth 1 -type f -name 'servidor_imap_mem*' -print -quit)"
[[ -n "$MEMORY_TEST" ]] || MEMORY_TEST="$SOURCE_TEST_DIR/servidor_imap_memoria.fe"
install -o "${SUDO_USER:-rafael}" -g "${SUDO_USER:-rafael}" -m 0644 \
    "$WORK/servidor_imap_memoria.fe" "$MEMORY_TEST"
install -o "${SUDO_USER:-rafael}" -g "${SUDO_USER:-rafael}" -m 0644 \
    "$WORK/arquitetura.md" "$SOURCE_ROOT/docs/ARQUITETURA-DO-ECOSSISTEMA.md"
systemctl start "$SERVICE"
wait_for_imap

/usr/local/bin/santafé -e \
    'local I=importe "correio.imap"; garanta(I.versão=="0.4.1"); mostre("IMAP_UID_FETCH_OK")'
systemctl is-active --quiet "$SERVICE"

PUBLISHING=0
echo "Correção IMAP 0.4.1 publicada e validada. Cópia de segurança: $BACKUP"
echo "UID FETCH agora sempre identifica a carta associada ao corpo retornado."
