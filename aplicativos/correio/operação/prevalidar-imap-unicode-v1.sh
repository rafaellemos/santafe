#!/usr/bin/env bash

set -Eeuo pipefail

PACKAGE="/tmp/santafe-imap-unicode-20260901-v1.tar.gz"
PUBLISHER="/tmp/publicar-imap-unicode-v1.sh"
EXPECTED_HASH="b5b85d6eee9af5498a477d248ac5e6fa615026e116006c01fd7e97e314171782"
INSTALLED_BIBF="/usr/local/share/santafé/1.0/bibf"
WORK=""

cleanup() {
    if [[ -n "$WORK" && -d "$WORK" ]]; then
        rm -rf -- "$WORK"
    fi
}
trap cleanup EXIT

ACTUAL_HASH="$(sha256sum "$PACKAGE" | awk '{print $1}')"
[[ "$ACTUAL_HASH" == "$EXPECTED_HASH" ]]
bash -n "$PUBLISHER"

WORK="$(mktemp -d /tmp/santafe-imap-unicode-preflight.XXXXXX)"
tar -xzf "$PACKAGE" -C "$WORK"
ROOT="$WORK/source"
install -d "$ROOT/testes/recursos"
openssl req -x509 -newkey rsa:2048 -nodes -days 1 \
    -subj '/CN=localhost' \
    -keyout "$ROOT/testes/recursos/tls-local-chave.pem" \
    -out "$ROOT/testes/recursos/tls-local-certificado.pem" \
    >/dev/null 2>&1
chmod 0600 "$ROOT/testes/recursos/tls-local-chave.pem"

LUA_PATH_TEST="$ROOT/bibs/bibf/?.fé;$ROOT/bibs/bibf/?/?.fé;$INSTALLED_BIBF/?.fé;$INSTALLED_BIBF/?/?.fé;;"
LUA_CPATH_TEST="/usr/local/lib/santafé/1.0/bibc/?.so;;"

echo "==> Sintaxe e versões"
/usr/local/bin/santafec -p "$ROOT/bibs/bibf/correio.fé"
/usr/local/bin/santafec -p "$ROOT/bibs/bibf/correio/agência.fé"
/usr/local/bin/santafec -p "$ROOT/bibs/bibf/correio/imap.fé"
/usr/local/bin/santafec -p \
    "$ROOT/testes/integração/servidor_imap_memória.fé"
grep -Fq 'versão = "0.5.0"' "$ROOT/bibs/bibf/correio.fé"
grep -Fq 'versão = "0.5.0"' "$ROOT/bibs/bibf/correio/imap.fé"

echo "==> Correio, MIME, Agência e submissão SMTPUTF8"
for test_file in \
    testes/bibf/teste_correio_agência.fé \
    testes/bibf/teste_correio_mime.fé \
    testes/bibf/teste_correio_seguranca.fé \
    testes/bibc/teste_correio_submissão_smtp.fé; do
    env GSETTINGS_BACKEND=memory LUA_PATH="$LUA_PATH_TEST" \
        LUA_CPATH="$LUA_CPATH_TEST" /usr/local/bin/santafé \
        "$ROOT/$test_file"
done

echo "==> IMAP estrito em servidor transitório"
(
    cd "$ROOT"
    env GSETTINGS_BACKEND=memory PYTHONDONTWRITEBYTECODE=1 \
        LUA_PATH="$LUA_PATH_TEST" LUA_CPATH="$LUA_CPATH_TEST" \
        python3 testes/integração/validar_imap.py \
            --santafe /usr/local/bin/santafé --porta 19995
)

echo "==> Manual"
(
    cd "$ROOT/site"
    python3 validar-manual.py manual.html \
        --compilador /usr/local/bin/santafec
)

echo "==> Rotas atuais que serão verificadas após a troca"
curl -fsS --max-time 8 http://127.0.0.1:7100/carteiro/ \
    -o "$WORK/carteiro-atual.html"
curl -kfsS --max-time 8 -H 'Host: xn--santaf-gva.dev.br' \
    https://127.0.0.1/estático/manual/ \
    -o "$WORK/manual-atual.html"

echo "PREVALIDACAO_CORREIO_IMAP_UNICODE_0_5_0_OK"
