#!/usr/bin/env bash

set -Eeuo pipefail

PACKAGE="/tmp/santafe-imap-gmail-20260901-v1.tar.gz"
PUBLISHER="/tmp/publicar-imap-gmail-v1.sh"
EXPECTED_HASH="fef501be4afb9e7a5e1529b5639da1f7e26652d852485daec11bac65bd090774"
INSTALLED_BIBF="/usr/local/share/santafé/1.0/bibf"
WORK=""

cleanup() {
    if [[ -n "$WORK" && -d "$WORK" ]]; then
        rm -rf -- "$WORK"
    fi
}
trap cleanup EXIT

[[ "$(sha256sum "$PACKAGE" | awk '{print $1}')" == "$EXPECTED_HASH" ]]
bash -n "$PUBLISHER"
WORK="$(mktemp -d /tmp/santafe-imap-gmail-preflight.XXXXXX)"
tar -xzf "$PACKAGE" -C "$WORK"
ROOT="$WORK/source"
install -d "$ROOT/testes/recursos"
openssl req -x509 -newkey rsa:2048 -nodes -days 1 \
    -subj '/CN=localhost' \
    -keyout "$ROOT/testes/recursos/tls-local-chave.pem" \
    -out "$ROOT/testes/recursos/tls-local-certificado.pem" \
    >/dev/null 2>&1
chmod 0600 "$ROOT/testes/recursos/tls-local-chave.pem"

/usr/local/bin/santafec -p "$ROOT/bibs/bibf/correio/imap.fé"
grep -Fq 'versão = "0.5.1"' "$ROOT/bibs/bibf/correio/imap.fé"
grep -Fq 'UTF8=ACCEPT' "$ROOT/bibs/bibf/correio/imap.fé"
if grep -Fq 'UTF8=ONLY' "$ROOT/bibs/bibf/correio/imap.fé"; then exit 1; fi

LUA_PATH_TEST="$ROOT/bibs/bibf/?.fé;$ROOT/bibs/bibf/?/?.fé;$INSTALLED_BIBF/?.fé;$INSTALLED_BIBF/?/?.fé;;"
(
    cd "$ROOT"
    env GSETTINGS_BACKEND=memory PYTHONDONTWRITEBYTECODE=1 \
        LUA_PATH="$LUA_PATH_TEST" \
        LUA_CPATH="/usr/local/lib/santafé/1.0/bibc/?.so;;" \
        python3 testes/integração/validar_imap.py \
            --santafe /usr/local/bin/santafé --porta 19995
)
(
    cd "$ROOT/site"
    python3 validar-manual.py manual.html \
        --compilador /usr/local/bin/santafec
)
echo "PREVALIDACAO_IMAP_GMAIL_0_5_1_OK"
