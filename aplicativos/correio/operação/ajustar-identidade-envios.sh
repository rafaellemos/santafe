#!/usr/bin/env bash

set -Eeuo pipefail

AMBIENTE=/etc/santafe/correio.env
UNIDADE=/etc/systemd/system/correio-envios.service
NOVA_UNIDADE=/tmp/correio-envios-validado.service
NOME_SMTP=xn--santaf-gva.dev.br
COPIA="/var/backups/santafe-correio-identidade-$(date +%Y%m%d-%H%M%S)"
ALTEROU=0

[[ "$EUID" -eq 0 ]] || {
    echo "Execute com sudo." >&2
    exit 1
}

restaure() {
    local codigo=$?
    trap - ERR
    if [[ "$ALTEROU" == 1 ]]; then
        cp -a "$COPIA/correio.env" "$AMBIENTE"
        cp -a "$COPIA/correio-envios.service" "$UNIDADE"
        systemctl daemon-reload
        echo "ERRO: configuração anterior restaurada. Cópia: $COPIA" >&2
    fi
    exit "$codigo"
}

trap restaure ERR

[[ -f "$AMBIENTE" ]] || {
    echo "ERRO: $AMBIENTE não existe." >&2
    exit 1
}
[[ -f "$UNIDADE" ]] || {
    echo "ERRO: $UNIDADE não existe." >&2
    exit 1
}
[[ -f "$NOVA_UNIDADE" ]] || {
    echo "ERRO: $NOVA_UNIDADE não existe." >&2
    exit 1
}

mkdir -p "$COPIA"
cp -a "$AMBIENTE" "$COPIA/correio.env"
cp -a "$UNIDADE" "$COPIA/correio-envios.service"
ALTEROU=1

temporario="$(mktemp /tmp/correio-env.XXXXXX)"
trap 'rm -f -- "$temporario"' EXIT
if grep -q '^CORREIO_ENVIOS_NOME=' "$AMBIENTE"; then
    sed "s|^CORREIO_ENVIOS_NOME=.*$|CORREIO_ENVIOS_NOME=$NOME_SMTP|" \
        "$AMBIENTE" > "$temporario"
else
    cp "$AMBIENTE" "$temporario"
    printf '\nCORREIO_ENVIOS_NOME=%s\n' "$NOME_SMTP" >> "$temporario"
fi
chown --reference="$AMBIENTE" "$temporario"
chmod --reference="$AMBIENTE" "$temporario"
mv -f "$temporario" "$AMBIENTE"

install -o root -g root -m 0644 "$NOVA_UNIDADE" "$UNIDADE"
systemctl daemon-reload

inicio="$(date '+%Y-%m-%d %H:%M:%S')"
systemctl start correio-envios.service
systemctl is-enabled --quiet correio-envios.timer
systemctl is-active --quiet correio-envios.timer

registros="$(journalctl -u correio-envios.service --since "$inicio" \
    --no-pager -l)"
if grep -q 'dconf' <<<"$registros"; then
    echo "ERRO: o processador ainda tentou usar dconf." >&2
    exit 1
fi

grep -q '^Environment=GSETTINGS_BACKEND=memory$' "$UNIDADE"
grep -q "^CORREIO_ENVIOS_NOME=$NOME_SMTP$" "$AMBIENTE"

ALTEROU=0
trap - ERR
echo "Identidade EHLO alinhada ao A/PTR e avisos do dconf removidos."
echo "Cópia de segurança: $COPIA"
