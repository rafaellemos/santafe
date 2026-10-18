#!/usr/bin/env bash

set -Eeuo pipefail

PULSO="/var/log/santafé/correio.pulso"
TEMP=""

cleanup() {
    if [[ -n "$TEMP" && -f "$TEMP" ]]; then rm -f -- "$TEMP"; fi
}
trap cleanup EXIT

[[ "$EUID" -eq 0 ]] || {
    echo "Execute com sudo." >&2
    exit 1
}
[[ -r "$PULSO" ]] || {
    echo "Registro PULSO não está legível: $PULSO" >&2
    exit 1
}

echo "==> Serviços"
for service in correio-imap.service correio-agencia.service \
    correio-envios.timer; do
    printf '%s: ' "$service"
    systemctl is-active "$service"
done

TEMP="$(mktemp /tmp/santafe-gmail-rascunhos.XXXXXX)"
tail -n 8000 "$PULSO" > "$TEMP"

echo "==> Sequência recente IMAP + Agência + CD"
python3 - "$TEMP" <<'PY'
import datetime
import json
import sys

path = sys.argv[1]
events = []
with open(path, encoding="utf-8", errors="replace") as stream:
    for line in stream:
        try:
            event = json.loads(line)
        except Exception:
            continue
        name = str(event.get("nome", ""))
        origin = str(event.get("origem", ""))
        relevant = (
            name.startswith("correio.imap")
            or "agencia" in origin.lower()
            or "agência" in origin.lower()
            or name in {
                "correio.autenticado",
                "correio.autenticaçãoRecusada",
                "correio.autenticaçãoIndisponível",
                "correio.autorizaçãoIndisponível",
                "correio.comandoRecusado",
                "correio.destinatárioMalformado",
                "correio.mensagemRecebida",
                "correio.persistênciaFalhou",
                "correio.cd.postagemRecusada",
                "correio.cd.cartaEnfileirada",
            }
        )
        if relevant:
            events.append(event)

allowed = {
    "endereço", "usuário", "comando", "pasta", "tamanho", "duplicada",
    "remetente", "destinatários", "falha", "tipo", "comandos", "rastro",
    "código", "motivo", "argumento",
}
for event in events[-180:]:
    timestamp = event.get("carimboDeHora")
    try:
        instant = datetime.datetime.fromtimestamp(
            int(timestamp), datetime.timezone.utc
        ).astimezone().isoformat(timespec="seconds")
    except Exception:
        instant = str(timestamp)
    data = event.get("dados") if isinstance(event.get("dados"), dict) else {}
    safe = {key: data[key] for key in allowed if key in data}
    print(
        instant,
        event.get("origem", "-"),
        event.get("nome", "-"),
        json.dumps(safe, ensure_ascii=False, separators=(",", ":")),
    )
PY

echo "==> Totais recentes relevantes"
grep -oE 'correio\.(imapCartaAnexada|imapUnicodeCompatibilidade|autenticado|autenticaçãoRecusada|autorizaçãoIndisponível|comandoRecusado|destinatárioMalformado|mensagemRecebida|persistênciaFalhou|cd\.postagemRecusada|cd\.cartaEnfileirada)' \
    "$TEMP" | sort | uniq -c || true
