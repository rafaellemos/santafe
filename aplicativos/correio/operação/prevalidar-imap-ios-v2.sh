#!/usr/bin/env bash

set -Eeuo pipefail

PACKAGE="/tmp/santafe-imap-ios-20260831-v2.tar.gz"
EXPECTED_HASH="4860ed501abbda6cf6b24e59068b42bccb8ca067036a9446d6301ac96c5dffa4"
WORK=""

cleanup() {
    [[ -z "$WORK" || ! -d "$WORK" ]] || rm -rf -- "$WORK"
}
trap cleanup EXIT

ACTUAL_HASH="$(sha256sum "$PACKAGE" | awk '{print $1}')"
[[ "$ACTUAL_HASH" == "$EXPECTED_HASH" ]]
bash -n /tmp/publicar-imap-ios-v2.sh

WORK="$(mktemp -d /tmp/santafe-imap-ios-preflight.XXXXXX)"
tar -xzf "$PACKAGE" -C "$WORK"
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

/usr/local/bin/santafec -p "$ROOT/bibs/bibf/correio/imap.fé"
/usr/local/bin/santafec -p \
    "$ROOT/testes/integração/servidor_imap_memória.fé"
cd "$ROOT"
PYTHONDONTWRITEBYTECODE=1 python3 testes/integração/validar_imap.py \
    --santafe /usr/local/bin/santafé --porta 19995
echo "PRÉ-VALIDAÇÃO_IMAP_IOS_0_4_3_OK"
