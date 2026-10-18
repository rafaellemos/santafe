#!/usr/bin/env bash

set -Eeuo pipefail

PULSO="/var/log/santafé/correio.pulso"

[[ "$EUID" -eq 0 ]] || {
    echo "Execute com sudo." >&2
    exit 1
}
[[ -r "$PULSO" ]] || {
    echo "Registro PULSO não está legível: $PULSO" >&2
    exit 1
}

echo "==> Serviço e porta IMAP"
systemctl is-active correio-imap.service
ss -ltnH 'sport = :993'

echo "==> Eventos IMAP recentes do PULSO"
tail -n 4000 "$PULSO" |
    grep -E '"nome":"correio\.imap(ConexãoAceita|Autenticado|UnicodeAtivado|UnicodeObrigatorio|ConexãoFechada)"' |
    tail -n 160 || true

echo "==> Contagem dos sinais Unicode recentes"
tail -n 4000 "$PULSO" |
    grep -oE 'correio\.imap(UnicodeAtivado|UnicodeObrigatorio)' |
    sort | uniq -c || true
