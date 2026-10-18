#!/usr/bin/env bash

set -Eeuo pipefail

PACKAGE="/tmp/santafe-apple-ios-20260831-v1.tar.gz"
EXPECTED_HASH="18c9649c7805666df8cda702b77b3ee2ad907cd66f3e2a36f3c3772c79023bd6"
SOURCE_ROOT="/home/${USER}/santafe-fonte"
INSTALLED_BIBF="/usr/local/share/santafé/1.0/bibf"
INSTALLED_BIBC="/usr/local/lib/santafé/1.0/bibc"
WORK=""

cleanup() {
    [[ -z "$WORK" || ! -d "$WORK" ]] || rm -rf -- "$WORK"
}
trap cleanup EXIT

ACTUAL_HASH="$(sha256sum "$PACKAGE" | awk '{print $1}')"
[[ "$ACTUAL_HASH" == "$EXPECTED_HASH" ]]
bash -n /tmp/publicar-apple-ios-v1.sh

WORK="$(mktemp -d /tmp/santafe-apple-ios-preflight.XXXXXX)"
tar -xzf "$PACKAGE" -C "$WORK"
ROOT="$WORK/raiz"
install -d \
    "$ROOT/bibs/bibf/correio" \
    "$ROOT/aplicativos/carteiro/fonte/carteiro" \
    "$ROOT/testes/bibf" "$ROOT/testes/bibc" \
    "$ROOT/testes/integração" "$ROOT/testes/recursos"
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

for source in \
    "$ROOT/bibs/bibf/correio/imap.fé" \
    "$ROOT/aplicativos/carteiro/fonte/carteiro/configurador.fé" \
    "$ROOT/aplicativos/carteiro/fonte/carteiro/aplicação.fé" \
    "$ROOT/aplicativos/carteiro/fonte/carteiro/páginas.fé" \
    "$ROOT/testes/bibf/teste_carteiro_configurador.fé" \
    "$ROOT/testes/bibc/teste_carteiro_http.fé" \
    "$ROOT/testes/integração/servidor_imap_memória.fé"; do
    /usr/local/bin/santafec -p "$source"
done

cd "$ROOT"
env \
    LUA_PATH="$ROOT/aplicativos/carteiro/fonte/?.fé;$SOURCE_ROOT/aplicativos/carteiro/fonte/?.fé;$SOURCE_ROOT/aplicativos/carteiro/fonte/?/ini.fé;$INSTALLED_BIBF/?.fé;$INSTALLED_BIBF/?/?.fé;;" \
    LUA_CPATH="$INSTALLED_BIBC/?.so;;" \
    /usr/local/bin/santafé testes/bibf/teste_carteiro_configurador.fé
env \
    LUA_PATH="$ROOT/aplicativos/carteiro/fonte/?.fé;$SOURCE_ROOT/aplicativos/carteiro/fonte/?.fé;$SOURCE_ROOT/aplicativos/carteiro/fonte/?/ini.fé;$INSTALLED_BIBF/?.fé;$INSTALLED_BIBF/?/?.fé;;" \
    LUA_CPATH="$INSTALLED_BIBC/?.so;;" \
    /usr/local/bin/santafé testes/bibc/teste_carteiro_http.fé
PYTHONDONTWRITEBYTECODE=1 python3 testes/integração/validar_imap.py \
    --santafe /usr/local/bin/santafé --porta 19994

echo "PRÉ-VALIDAÇÃO_APPLE_IOS_OK"
