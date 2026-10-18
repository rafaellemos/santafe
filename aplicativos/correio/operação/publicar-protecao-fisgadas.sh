#!/usr/bin/env bash

set -Eeuo pipefail

PACOTE="/tmp/santafe-protecao-fisgadas-20260830.tar.gz"
SOMA="${PACOTE}.sha256"
RAIZ_PACOTE="santafe-protecao-fisgadas-20260830"
FONTE_SERVIDOR="/home/${SUDO_USER:-rafael}/santafe-fonte"
DESTINO_BIBF="/usr/local/share/santafé/1.0/bibf"
DESTINO_CORREIO="/opt/correio"
DESTINO_CARTEIRO="/opt/carteiro"
DESTINO_MANUAL="/var/www/santafé.dev.br/estático/manual/index.html"
SERVICO="correio-recebedor.service"

TRABALHO=""
COPIA=""
PUBLICANDO=0

ALVOS=(
    "$DESTINO_BIBF/correio/triagem.fé"
    "$DESTINO_BIBF/correio/LEIA-ME.md"
    "$DESTINO_CORREIO/LEIA-ME.md"
    "$DESTINO_CARTEIRO/LEIA-ME.md"
    "$DESTINO_MANUAL"
    "$FONTE_SERVIDOR/bibs/bibf/correio/triagem.fé"
    "$FONTE_SERVIDOR/bibs/bibf/correio/LEIA-ME.md"
    "$FONTE_SERVIDOR/aplicativos/correio/LEIA-ME.md"
    "$FONTE_SERVIDOR/aplicativos/carteiro/LEIA-ME.md"
    "$FONTE_SERVIDOR/testes/bibf/teste_correio_triagem.fé"
    "$FONTE_SERVIDOR/testes/bibf/auditar_fisgada_atual.fé"
    "$FONTE_SERVIDOR/site-sfdev/manual.html"
)

limpar() {
    if [[ -n "$TRABALHO" && -d "$TRABALHO" ]]; then
        rm -rf -- "$TRABALHO"
    fi
}

restaurar() {
    trap - ERR
    set +e
    echo "ERRO: publicação interrompida; restaurando os arquivos anteriores." >&2
    systemctl stop "$SERVICO" 2>/dev/null || true
    if [[ -f "$COPIA/antes.tar.gz" ]]; then
        tar -xzf "$COPIA/antes.tar.gz" -C /
    fi
    if [[ -f "$COPIA/ausentes.txt" ]]; then
        while IFS= read -r alvo; do
            [[ -n "$alvo" ]] && rm -f -- "$alvo"
        done < "$COPIA/ausentes.txt"
    fi
    systemctl start "$SERVICO" || true
    echo "Versão anterior restaurada. Cópia de segurança: $COPIA" >&2
}

ao_falhar() {
    codigo=$?
    linha=$1
    comando=$2
    trap - ERR
    echo "Falha na linha $linha (código $codigo): $comando" >&2
    systemctl status "$SERVICO" --no-pager -l >&2 || true
    if [[ "$PUBLICANDO" -eq 1 ]]; then restaurar; fi
    exit "$codigo"
}

trap limpar EXIT
trap 'ao_falhar "$LINENO" "$BASH_COMMAND"' ERR

[[ "$EUID" -eq 0 ]] || { echo "Execute com sudo." >&2; exit 1; }
[[ -f "$PACOTE" && -f "$SOMA" ]] || {
    echo "Pacote ou soma ausente em /tmp." >&2
    exit 1
}
systemctl is-active --quiet "$SERVICO" || {
    echo "$SERVICO não está ativo; nada foi alterado." >&2
    exit 1
}

echo "==> Conferindo o pacote e a Triagem 1.1"
(cd /tmp && sha256sum -c "$(basename "$SOMA")")
TRABALHO="$(mktemp -d /tmp/santafe-fisgadas.XXXXXX)"
tar -xzf "$PACOTE" -C "$TRABALHO"
RAIZ="$TRABALHO/$RAIZ_PACOTE"

OBRIGATORIOS=(
    bibs/bibf/correio/triagem.fe
    bibs/bibf/correio/LEIA-ME.md
    aplicativos/correio/LEIA-ME.md
    aplicativos/carteiro/LEIA-ME.md
    testes/bibf/teste_correio_triagem.fe
    testes/bibf/auditar_fisgada_atual.fe
    site/manual.html
    site/validar-manual.py
)
for relativo in "${OBRIGATORIOS[@]}"; do
    [[ -f "$RAIZ/$relativo" ]] || {
        echo "Arquivo ausente no pacote: $relativo" >&2
        exit 1
    }
done

/usr/local/bin/santafec -p "$RAIZ/bibs/bibf/correio/triagem.fe"
(
    cd "$RAIZ"
    export LUA_PATH="$RAIZ/bibs/bibf/?.fe;$RAIZ/bibs/bibf/?/?.fe;$DESTINO_BIBF/?.fé;$DESTINO_BIBF/?/?.fé;;"
    export LUA_CPATH="/usr/local/lib/santafé/1.0/bibc/?.so;;"
    /usr/local/bin/santafé testes/bibf/teste_correio_triagem.fe
    /usr/local/bin/santafé testes/bibf/auditar_fisgada_atual.fe
)
python3 "$RAIZ/site/validar-manual.py" "$RAIZ/site/manual.html" \
    --compilador /usr/local/bin/santafec

echo "==> Criando cópia de segurança"
COPIA="/var/backups/santafe-fisgadas-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$COPIA"
: > "$COPIA/ausentes.txt"
EXISTENTES=()
for alvo in "${ALVOS[@]}"; do
    if [[ -e "$alvo" ]]; then
        EXISTENTES+=("$alvo")
    else
        printf '%s\n' "$alvo" >> "$COPIA/ausentes.txt"
    fi
done
if [[ "${#EXISTENTES[@]}" -gt 0 ]]; then
    tar -czf "$COPIA/antes.tar.gz" "${EXISTENTES[@]}"
fi

PUBLICANDO=1
echo "==> Instalando a proteção contra fisgadas"
systemctl stop "$SERVICO"

install -o root -g root -m 0644 \
    "$RAIZ/bibs/bibf/correio/triagem.fe" \
    "$DESTINO_BIBF/correio/triagem.fé"
install -o root -g root -m 0644 \
    "$RAIZ/bibs/bibf/correio/LEIA-ME.md" \
    "$DESTINO_BIBF/correio/LEIA-ME.md"
install -o root -g correio -m 0640 \
    "$RAIZ/aplicativos/correio/LEIA-ME.md" \
    "$DESTINO_CORREIO/LEIA-ME.md"
install -o root -g carteiro -m 0640 \
    "$RAIZ/aplicativos/carteiro/LEIA-ME.md" \
    "$DESTINO_CARTEIRO/LEIA-ME.md"
install -o root -g www-data -m 0644 \
    "$RAIZ/site/manual.html" "$DESTINO_MANUAL"

DONO="${SUDO_USER:-rafael}"
GRUPO="$(id -gn "$DONO")"
mkdir -p "$FONTE_SERVIDOR/bibs/bibf/correio" \
    "$FONTE_SERVIDOR/aplicativos/correio" \
    "$FONTE_SERVIDOR/aplicativos/carteiro" \
    "$FONTE_SERVIDOR/testes/bibf"
install -o "$DONO" -g "$GRUPO" -m 0644 \
    "$RAIZ/bibs/bibf/correio/triagem.fe" \
    "$FONTE_SERVIDOR/bibs/bibf/correio/triagem.fé"
install -o "$DONO" -g "$GRUPO" -m 0644 \
    "$RAIZ/testes/bibf/teste_correio_triagem.fe" \
    "$FONTE_SERVIDOR/testes/bibf/teste_correio_triagem.fé"
install -o "$DONO" -g "$GRUPO" -m 0644 \
    "$RAIZ/testes/bibf/auditar_fisgada_atual.fe" \
    "$FONTE_SERVIDOR/testes/bibf/auditar_fisgada_atual.fé"
for relativo in \
    bibs/bibf/correio/LEIA-ME.md \
    aplicativos/correio/LEIA-ME.md \
    aplicativos/carteiro/LEIA-ME.md; do
    mkdir -p "$(dirname "$FONTE_SERVIDOR/$relativo")"
    install -o "$DONO" -g "$GRUPO" -m 0644 \
        "$RAIZ/$relativo" "$FONTE_SERVIDOR/$relativo"
done
mkdir -p "$FONTE_SERVIDOR/site-sfdev"
install -o "$DONO" -g "$GRUPO" -m 0644 \
    "$RAIZ/site/manual.html" "$FONTE_SERVIDOR/site-sfdev/manual.html"

echo "==> Reiniciando e validando o Correio"
systemctl start "$SERVICO"
PRONTO=0
for _ in $(seq 1 80); do
    if systemctl is-active --quiet "$SERVICO"; then
        ss -H -ltn 'sport = :25' > "$TRABALHO/porta-25.txt"
        if [[ -s "$TRABALHO/porta-25.txt" ]]; then
            PRONTO=1
            break
        fi
    fi
    sleep 0.25
done
[[ "$PRONTO" -eq 1 ]]

(
    cd /
    export LUA_PATH="$DESTINO_BIBF/?.fé;$DESTINO_BIBF/?/?.fé;;"
    export LUA_CPATH="/usr/local/lib/santafé/1.0/bibc/?.so;;"
    /usr/local/bin/santafé "$RAIZ/testes/bibf/auditar_fisgada_atual.fe"
    /usr/local/bin/santafé -e \
        'local t=importe "correio.triagem"; garanta(t.versão=="1.1.0"); mostre("Triagem instalada:",t.versão)'
)
python3 "$RAIZ/site/validar-manual.py" "$DESTINO_MANUAL" \
    --compilador /usr/local/bin/santafec

PUBLICANDO=0
echo "Proteção contra fisgadas publicada e validada."
echo "Cópia de segurança: $COPIA"
echo "Ligações mascaradas, formulários, IPs e esquemas perigosos agora são explicados pela Triagem."
