#!/usr/bin/env bash

set -Eeuo pipefail

PACKAGE="/tmp/santafe-apple-ios-20260831-v1.tar.gz"
EXPECTED_HASH="18c9649c7805666df8cda702b77b3ee2ad907cd66f3e2a36f3c3772c79023bd6"
SOURCE_ROOT="/home/${SUDO_USER:-rafael}/santafe-fonte"
IMAP_SERVICE="correio-imap.service"
CARTEIRO_SERVICE="carteiro.service"
CARTEIRO_ROOT="/opt/carteiro"
INSTALLED_BIBF="/usr/local/share/santafé/1.0/bibf"
INSTALLED_BIBC="/usr/local/lib/santafé/1.0/bibc"

WORK=""
ROOT=""
BACKUP=""
PUBLISHING=0
DEST_IMAP=""
SOURCE_IMAP=""

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
        echo "ERRO: atualização Apple/iPhone interrompida; restaurando a versão anterior."
        systemctl stop "$IMAP_SERVICE" "$CARTEIRO_SERVICE" \
            >/dev/null 2>&1 || true
        tar -xzf "$BACKUP/antes.tar.gz" -C /
        systemctl start "$IMAP_SERVICE" "$CARTEIRO_SERVICE" \
            >/dev/null 2>&1 || true
        echo "Versão anterior restaurada. Cópia de segurança: $BACKUP"
    fi
    exit "$code"
}

wait_for_services() {
    local counter state_file="$WORK/carteiro-estado.json"
    for ((counter=1; counter<=160; counter++)); do
        if systemctl is-active --quiet "$IMAP_SERVICE" &&
           systemctl is-active --quiet "$CARTEIRO_SERVICE" &&
           [[ -n "$(ss -ltnH 'sport = :993')" ]] &&
           curl -fsS --max-time 2 -o "$state_file" \
               http://127.0.0.1:7100/carteiro/estado 2>/dev/null &&
           grep -Fq '"estado":"pronto"' "$state_file"; then
            return 0
        fi
        if systemctl is-failed --quiet "$IMAP_SERVICE" ||
           systemctl is-failed --quiet "$CARTEIRO_SERVICE"; then
            break
        fi
        sleep 0.25
    done
    systemctl status "$IMAP_SERVICE" "$CARTEIRO_SERVICE" \
        --no-pager -l >&2 || true
    journalctl -u "$IMAP_SERVICE" -u "$CARTEIRO_SERVICE" \
        -n 120 --no-pager -l >&2 || true
    return 1
}

trap cleanup EXIT
trap 'restore_previous "$?" "$LINENO" "$BASH_COMMAND"' ERR

[[ "$EUID" -eq 0 ]] || { echo "Execute com sudo." >&2; exit 1; }
echo "Publicador Apple/iPhone v1.0 — perfil iOS e diagnóstico IMAP 0.4.2"
[[ -f "$PACKAGE" ]] || { echo "Pacote ausente: $PACKAGE" >&2; exit 1; }
ACTUAL_HASH="$(sha256sum "$PACKAGE" | awk '{print $1}')"
[[ "$ACTUAL_HASH" == "$EXPECTED_HASH" ]] || {
    echo "A soma do pacote não confere; nada foi alterado." >&2
    exit 1
}
systemctl is-active --quiet "$IMAP_SERVICE" || {
    echo "$IMAP_SERVICE não está ativo; nada foi alterado." >&2
    exit 1
}
systemctl is-active --quiet "$CARTEIRO_SERVICE" || {
    echo "$CARTEIRO_SERVICE não está ativo; nada foi alterado." >&2
    exit 1
}

WORK="$(mktemp -d /tmp/santafe-apple-ios-publicacao.XXXXXX)"
tar -xzf "$PACKAGE" -C "$WORK"
REQUIRED=(
    "imap.fe"
    "configurador.fe"
    "aplicacao.fe"
    "paginas.fe"
    "teste_configurador.fe"
    "teste_http.fe"
    "validar_imap.py"
    "servidor_imap_memoria.fe"
    "certificado.pem"
    "chave.pem"
    "arquitetura.md"
)
for relative in "${REQUIRED[@]}"; do
    [[ -f "$WORK/$relative" ]] || {
        echo "Arquivo ausente no pacote: $relative" >&2
        exit 1
    }
done

# O pacote usa somente nomes ASCII para atravessar macOS e Linux sem
# divergência de normalização Unicode. A árvore Santafé é reconstruída aqui.
ROOT="$WORK/raiz"
install -d \
    "$ROOT/bibs/bibf/correio" \
    "$ROOT/aplicativos/carteiro/fonte/carteiro" \
    "$ROOT/testes/bibf" "$ROOT/testes/bibc" \
    "$ROOT/testes/integração" "$ROOT/testes/recursos" "$ROOT/docs"
install -m 0644 "$WORK/imap.fe" "$ROOT/bibs/bibf/correio/imap.fé"
install -m 0644 "$WORK/configurador.fe" \
    "$ROOT/aplicativos/carteiro/fonte/carteiro/configurador.fé"
install -m 0644 "$WORK/aplicacao.fe" \
    "$ROOT/aplicativos/carteiro/fonte/carteiro/aplicação.fé"
install -m 0644 "$WORK/paginas.fe" \
    "$ROOT/aplicativos/carteiro/fonte/carteiro/páginas.fé"
install -m 0644 "$WORK/teste_configurador.fe" \
    "$ROOT/testes/bibf/teste_carteiro_configurador.fé"
install -m 0644 "$WORK/teste_http.fe" \
    "$ROOT/testes/bibc/teste_carteiro_http.fé"
install -m 0644 "$WORK/validar_imap.py" \
    "$ROOT/testes/integração/validar_imap.py"
install -m 0644 "$WORK/servidor_imap_memoria.fe" \
    "$ROOT/testes/integração/servidor_imap_memória.fé"
install -m 0644 "$WORK/certificado.pem" \
    "$ROOT/testes/recursos/tls-local-certificado.pem"
install -m 0600 "$WORK/chave.pem" \
    "$ROOT/testes/recursos/tls-local-chave.pem"
install -m 0644 "$WORK/arquitetura.md" \
    "$ROOT/docs/ARQUITETURA-DO-ECOSSISTEMA.md"

DEST_IMAP="$(find "$INSTALLED_BIBF/correio" -maxdepth 1 \
    -type f -name 'imap.*' -print -quit)"
SOURCE_IMAP="$(find "$SOURCE_ROOT/bibs/bibf/correio" -maxdepth 1 \
    -type f -name 'imap.*' -print -quit)"
[[ -n "$DEST_IMAP" && -f "$DEST_IMAP" ]] || {
    echo "Módulo IMAP instalado não encontrado." >&2
    exit 1
}
[[ -n "$SOURCE_IMAP" && -f "$SOURCE_IMAP" ]] || {
    echo "Fonte IMAP do servidor não encontrada." >&2
    exit 1
}

echo "==> Validando fontes, perfis Apple, HTTP e IMAP antes da troca"
for relative in \
    "bibs/bibf/correio/imap.fé" \
    "aplicativos/carteiro/fonte/carteiro/configurador.fé" \
    "aplicativos/carteiro/fonte/carteiro/aplicação.fé" \
    "aplicativos/carteiro/fonte/carteiro/páginas.fé" \
    "testes/bibf/teste_carteiro_configurador.fé" \
    "testes/bibc/teste_carteiro_http.fé" \
    "testes/integração/servidor_imap_memória.fé"; do
    /usr/local/bin/santafec -p "$ROOT/$relative"
done
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
    "$ROOT/testes/integração/validar_imap.py"
grep -F 'versão = "0.4.2"' "$ROOT/bibs/bibf/correio/imap.fé" >/dev/null
grep -F 'rastro = sessão.rastro' "$ROOT/bibs/bibf/correio/imap.fé" >/dev/null
grep -F 'local tipoDoAparelho = alvo == "mac" e 5 ou 1' \
    "$ROOT/aplicativos/carteiro/fonte/carteiro/configurador.fé" >/dev/null

(
    cd "$ROOT"
    env \
        LUA_PATH="$ROOT/aplicativos/carteiro/fonte/?.fé;$CARTEIRO_ROOT/fonte/?.fé;$CARTEIRO_ROOT/fonte/?/ini.fé;$INSTALLED_BIBF/?.fé;$INSTALLED_BIBF/?/?.fé;;" \
        LUA_CPATH="$INSTALLED_BIBC/?.so;;" \
        /usr/local/bin/santafé testes/bibf/teste_carteiro_configurador.fé
    env \
        LUA_PATH="$ROOT/aplicativos/carteiro/fonte/?.fé;$CARTEIRO_ROOT/fonte/?.fé;$CARTEIRO_ROOT/fonte/?/ini.fé;$INSTALLED_BIBF/?.fé;$INSTALLED_BIBF/?/?.fé;;" \
        LUA_CPATH="$INSTALLED_BIBC/?.so;;" \
        /usr/local/bin/santafé testes/bibc/teste_carteiro_http.fé
    PYTHONDONTWRITEBYTECODE=1 python3 testes/integração/validar_imap.py \
        --santafe /usr/local/bin/santafé --porta 19994
)

BACKUP="/var/backups/santafe-apple-ios-$(date +%Y%m%d-%H%M%S)"
install -d -m 0700 "$BACKUP"
BACKUP_PATHS=(
    "${DEST_IMAP#/}"
    "opt/carteiro/fonte/carteiro/configurador.fé"
    "opt/carteiro/fonte/carteiro/aplicação.fé"
    "opt/carteiro/fonte/carteiro/páginas.fé"
    "${SOURCE_IMAP#/}"
    "${SOURCE_ROOT#/}/aplicativos/carteiro/fonte/carteiro/configurador.fé"
    "${SOURCE_ROOT#/}/aplicativos/carteiro/fonte/carteiro/aplicação.fé"
    "${SOURCE_ROOT#/}/aplicativos/carteiro/fonte/carteiro/páginas.fé"
    "${SOURCE_ROOT#/}/testes/bibf/teste_carteiro_configurador.fé"
    "${SOURCE_ROOT#/}/testes/bibc/teste_carteiro_http.fé"
    "${SOURCE_ROOT#/}/testes/integração/validar_imap.py"
    "${SOURCE_ROOT#/}/testes/integração/servidor_imap_memória.fé"
    "${SOURCE_ROOT#/}/docs/ARQUITETURA-DO-ECOSSISTEMA.md"
)
for path in "${BACKUP_PATHS[@]}"; do
    [[ -f "/$path" ]] || {
        echo "Arquivo de produção ausente: /$path" >&2
        exit 1
    }
done
tar -czf "$BACKUP/antes.tar.gz" -C / "${BACKUP_PATHS[@]}"

PUBLISHING=1
echo "==> Instalando o perfil específico do iPhone e o rastro IMAP seguro"
systemctl stop "$IMAP_SERVICE" "$CARTEIRO_SERVICE"
install -o root -g root -m 0644 \
    "$ROOT/bibs/bibf/correio/imap.fé" "$DEST_IMAP"
for name in configurador.fé aplicação.fé páginas.fé; do
    install -o root -g carteiro -m 0640 \
        "$ROOT/aplicativos/carteiro/fonte/carteiro/$name" \
        "$CARTEIRO_ROOT/fonte/carteiro/$name"
done
systemctl start "$IMAP_SERVICE" "$CARTEIRO_SERVICE"
wait_for_services

/usr/local/bin/santafé -e \
    'local I=importe "correio.imap"; garanta(I.versão=="0.4.2"); mostre("IMAP_0_4_2_OK")'
grep -Fq 'alvo = "iphone"' \
    "$CARTEIRO_ROOT/fonte/carteiro/aplicação.fé"
grep -Fq 'correio-santafe-mac.mobileconfig' \
    "$CARTEIRO_ROOT/fonte/carteiro/aplicação.fé"
grep -Fq 'Baixar para iPhone/iPad' \
    "$CARTEIRO_ROOT/fonte/carteiro/páginas.fé"

echo "==> Atualizando a árvore-fonte do servidor"
OWNER="${SUDO_USER:-rafael}"
GROUP="$(id -gn "$OWNER")"
install -o "$OWNER" -g "$GROUP" -m 0644 \
    "$ROOT/bibs/bibf/correio/imap.fé" "$SOURCE_IMAP"
for name in configurador.fé aplicação.fé páginas.fé; do
    install -o "$OWNER" -g "$GROUP" -m 0644 \
        "$ROOT/aplicativos/carteiro/fonte/carteiro/$name" \
        "$SOURCE_ROOT/aplicativos/carteiro/fonte/carteiro/$name"
done
install -o "$OWNER" -g "$GROUP" -m 0644 \
    "$ROOT/testes/bibf/teste_carteiro_configurador.fé" \
    "$SOURCE_ROOT/testes/bibf/teste_carteiro_configurador.fé"
install -o "$OWNER" -g "$GROUP" -m 0644 \
    "$ROOT/testes/bibc/teste_carteiro_http.fé" \
    "$SOURCE_ROOT/testes/bibc/teste_carteiro_http.fé"
install -o "$OWNER" -g "$GROUP" -m 0644 \
    "$ROOT/testes/integração/validar_imap.py" \
    "$SOURCE_ROOT/testes/integração/validar_imap.py"
install -o "$OWNER" -g "$GROUP" -m 0644 \
    "$ROOT/testes/integração/servidor_imap_memória.fé" \
    "$SOURCE_ROOT/testes/integração/servidor_imap_memória.fé"
install -o "$OWNER" -g "$GROUP" -m 0644 \
    "$ROOT/docs/ARQUITETURA-DO-ECOSSISTEMA.md" \
    "$SOURCE_ROOT/docs/ARQUITETURA-DO-ECOSSISTEMA.md"

systemctl is-active --quiet "$IMAP_SERVICE"
systemctl is-active --quiet "$CARTEIRO_SERVICE"
PUBLISHING=0
trap - ERR
echo "Perfil Apple/iPhone e IMAP 0.4.2 publicados e validados."
echo "Cópia de segurança: $BACKUP"
echo "Remova o perfil antigo do iPhone e instale novamente pelo Carteiro."
