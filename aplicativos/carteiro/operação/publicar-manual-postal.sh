#!/usr/bin/env bash
set -Eeuo pipefail

NOVO="${1:-/tmp/manual-pulso-20260829.html}"
RESUMO="4e32deb1759e7e3ec0e227569203addddb370f653d9f0c228f8bd31e56b33ebb"
DESTINO="/var/www/santafé.dev.br/estático/manual/index.html"
COPIA="/var/backups/santafe-manual-postal-$(date +%Y%m%d-%H%M%S)"
ALTEROU=0
TEMPORARIO="$(mktemp /tmp/manual-postal-publicado.XXXXXX)"

limpe() { rm -f -- "$TEMPORARIO"; }

restaure() {
    local codigo="$?"
    trap - ERR
    if [[ "$ALTEROU" == 1 && -f "$COPIA/index.html" ]]; then
        install -o www-data -g www-data -m 0644 "$COPIA/index.html" "$DESTINO"
        echo "ERRO: manual anterior restaurado. Cópia: $COPIA" >&2
    fi
    limpe
    exit "$codigo"
}

trap limpe EXIT
trap restaure ERR

valide_manual() {
    local arquivo="$1"
    grep -q 'id="lib-correio"' "$arquivo"
    grep -q 'id="lib-carteiro"' "$arquivo"
    grep -q 'id="correio-antivirus-examine"' "$arquivo"
    grep -q 'id="correio-deposito-leia"' "$arquivo"
    grep -q 'id="correio-dkim-assine"' "$arquivo"
    grep -q 'id="correio-cd-poste"' "$arquivo"
    grep -q 'id="correio-mariadb-receba-smtp"' "$arquivo"
    grep -q 'id="correio-util-nome-anexo"' "$arquivo"
    grep -q 'id="carteiro-enviar"' "$arquivo"
    grep -q 'id="c-arquivo"' "$arquivo"
    grep -q 'id="arquivo-grave-permissoes"' "$arquivo"
    grep -q 'id="arquivo-crie-diretorios-permissoes"' "$arquivo"
    grep -q 'id="lib-pulso"' "$arquivo"
    grep -q 'id="pulso-codifique"' "$arquivo"
    grep -q 'id="pulso-canal-operacao"' "$arquivo"
    grep -q 'id="pulso-registrador"' "$arquivo"
    grep -q 'id="pulso-destino-feche"' "$arquivo"
    [[ "$(grep -c 'class="sf-fn-row" id="correio-' "$arquivo")" -eq 63 ]]
    [[ "$(grep -c 'class="sf-fn-row" id="carteiro-' "$arquivo")" -eq 10 ]]
    [[ "$(grep -c 'class="sf-fn-row" id="arquivo-' "$arquivo")" -eq 8 ]]
    [[ "$(grep -c 'class="sf-fn-row" id="pulso-' "$arquivo")" -eq 25 ]]
}

echo "$RESUMO  $NOVO" | sha256sum -c -
valide_manual "$NOVO"

mkdir -p "$COPIA"
cp -a "$DESTINO" "$COPIA/index.html"
ALTEROU=1
install -o www-data -g www-data -m 0644 "$NOVO" "$DESTINO"
echo "$RESUMO  $DESTINO" | sha256sum -c -

curl -fsS --max-time 12 \
    https://xn--santaf-gva.dev.br/estático/manual/ > "$TEMPORARIO"
valide_manual "$TEMPORARIO"

ALTEROU=0
trap - ERR
echo "Manual do PULSO publicado e validado. Cópia de segurança: $COPIA"
