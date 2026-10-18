#!/usr/bin/env bash

set -Eeuo pipefail

PACOTE="/tmp/santafe-vigia-20260830.tar.gz"
SOMA="${PACOTE}.sha256"
RAIZ_PACOTE="santafe-vigia-20260830"
DESTINO_BIBF="/usr/local/share/santafé/1.0/bibf"
DESTINO_MANUAL="/var/www/santafé.dev.br/estático/manual/index.html"
FONTE_SERVIDOR="/home/${SUDO_USER:-rafael}/santafe-fonte"
TRABALHO=""
COPIA=""
PUBLICANDO=0
TINHA_VIGIA=0
TINHA_DOC_VIGIA=0

falhou() {
    local linha="$1"
    local codigo="$2"
    printf 'ERRO: publicação do Vigia interrompida na linha %s (código %s).\n' \
        "$linha" "$codigo" >&2
    se_necessario_restaurar
    exit "$codigo"
}

se_necessario_restaurar() {
    if [[ "$PUBLICANDO" -ne 1 || -z "$COPIA" || ! -d "$COPIA" ]]; then
        return
    fi
    trap - ERR
    set +e
    echo "Restaurando a versão anterior..."
    systemctl stop correio-recebedor.service carteiro.service
    install -m 0644 -o root -g root "$COPIA/correio.fé" \
        "$DESTINO_BIBF/correio.fé"
    install -m 0644 -o root -g root "$COPIA/correio-LEIA-ME.md" \
        "$DESTINO_BIBF/correio/LEIA-ME.md"
    install -m 0644 -o root -g root "$COPIA/pulso-LEIA-ME.md" \
        "$DESTINO_BIBF/pulso/LEIA-ME.md"
    install -m 0644 -o root -g www-data "$COPIA/manual.html" \
        "$DESTINO_MANUAL"
    if [[ "$TINHA_VIGIA" -eq 1 ]]; then
        install -m 0644 -o root -g root "$COPIA/vigia.fé" \
            "$DESTINO_BIBF/vigia.fé"
    else
        rm -f "$DESTINO_BIBF/vigia.fé"
    fi
    if [[ "$TINHA_DOC_VIGIA" -eq 1 ]]; then
        mkdir -p "$DESTINO_BIBF/vigia"
        install -m 0644 -o root -g root "$COPIA/vigia-LEIA-ME.md" \
            "$DESTINO_BIBF/vigia/LEIA-ME.md"
    else
        rm -f "$DESTINO_BIBF/vigia/LEIA-ME.md"
        rmdir "$DESTINO_BIBF/vigia" 2>/dev/null || true
    fi
    systemctl start correio-recebedor.service carteiro.service
    echo "Versão anterior restaurada. Cópia de segurança: $COPIA"
}

trap 'falhou "$LINENO" "$?"' ERR

[[ "${EUID}" -eq 0 ]] || { echo "Execute com sudo." >&2; exit 1; }
[[ -f "$PACOTE" && -f "$SOMA" ]] || {
    echo "Pacote ou soma ausente em /tmp." >&2; exit 1;
}

(cd /tmp && sha256sum -c "$(basename "$SOMA")")
TRABALHO="$(mktemp -d /tmp/santafe-vigia-publicacao.XXXXXX)"
trap 'rm -rf -- "$TRABALHO"' EXIT
tar -xzf "$PACOTE" -C "$TRABALHO"
RAIZ="$TRABALHO/$RAIZ_PACOTE"

echo "==> Validando fontes e comportamento antes da troca"
/usr/local/bin/santafec -p "$RAIZ/bibs/bibf/vigia.fé"
/usr/local/bin/santafec -p "$RAIZ/bibs/bibf/correio.fé"
/usr/local/bin/santafec -p "$RAIZ/testes/bibf/teste_vigia.fé"
LUA_PATH="$RAIZ/bibs/bibf/?.fé;$DESTINO_BIBF/?.fé;$DESTINO_BIBF/?/ini.fé;;" \
    /usr/local/bin/santafé "$RAIZ/testes/bibf/teste_vigia.fé"
python3 "$RAIZ/site/validar-manual.py" "$RAIZ/site/manual.html" \
    --compilador /usr/local/bin/santafec

COPIA="/var/backups/santafe-vigia-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$COPIA"
cp -a "$DESTINO_BIBF/correio.fé" "$COPIA/correio.fé"
cp -a "$DESTINO_BIBF/correio/LEIA-ME.md" "$COPIA/correio-LEIA-ME.md"
cp -a "$DESTINO_BIBF/pulso/LEIA-ME.md" "$COPIA/pulso-LEIA-ME.md"
cp -a "$DESTINO_MANUAL" "$COPIA/manual.html"
if [[ -f "$DESTINO_BIBF/vigia.fé" ]]; then
    TINHA_VIGIA=1
    cp -a "$DESTINO_BIBF/vigia.fé" "$COPIA/vigia.fé"
fi
if [[ -f "$DESTINO_BIBF/vigia/LEIA-ME.md" ]]; then
    TINHA_DOC_VIGIA=1
    cp -a "$DESTINO_BIBF/vigia/LEIA-ME.md" "$COPIA/vigia-LEIA-ME.md"
fi

PUBLICANDO=1
echo "==> Parando somente os consumidores postais persistentes"
systemctl stop correio-recebedor.service carteiro.service

echo "==> Instalando Vigia, Correio e documentação"
mkdir -p "$DESTINO_BIBF/vigia"
install -m 0644 -o root -g root "$RAIZ/bibs/bibf/vigia.fé" \
    "$DESTINO_BIBF/vigia.fé"
install -m 0644 -o root -g root "$RAIZ/bibs/bibf/correio.fé" \
    "$DESTINO_BIBF/correio.fé"
install -m 0644 -o root -g root "$RAIZ/bibs/bibf/vigia/LEIA-ME.md" \
    "$DESTINO_BIBF/vigia/LEIA-ME.md"
install -m 0644 -o root -g root "$RAIZ/bibs/bibf/correio/LEIA-ME.md" \
    "$DESTINO_BIBF/correio/LEIA-ME.md"
install -m 0644 -o root -g root "$RAIZ/bibs/bibf/pulso/LEIA-ME.md" \
    "$DESTINO_BIBF/pulso/LEIA-ME.md"
install -m 0644 -o root -g www-data "$RAIZ/site/manual.html" \
    "$DESTINO_MANUAL"

echo "==> Reiniciando e validando Correio e Carteiro"
systemctl start correio-recebedor.service carteiro.service
for tentativa in {1..30}; do
    if systemctl is-active --quiet correio-recebedor.service &&
       systemctl is-active --quiet carteiro.service &&
       curl -fsS --max-time 2 http://127.0.0.1:7100/carteiro/ >/dev/null 2>&1; then
        break
    fi
    sleep 1
done
systemctl is-active --quiet correio-recebedor.service
systemctl is-active --quiet carteiro.service
curl -fsS --max-time 5 http://127.0.0.1:7100/carteiro/ >/dev/null
timeout 5 bash -c 'exec 3<>/dev/tcp/127.0.0.1/25; IFS= read -r linha <&3; [[ "$linha" == 220* ]]'
grep -q 'id="lib-vigia"' "$DESTINO_MANUAL"
grep -q 'vigia.limiteAtingido' "$DESTINO_MANUAL"
sudo -u correio env LUA_PATH="$DESTINO_BIBF/?.fé;$DESTINO_BIBF/?/ini.fé;;" \
    /usr/local/bin/santafé -e 'local V = importe "vigia"; local p = garanta(V.novo()); garanta(p:admita("ensaio")); garanta(p:conclua("ensaio")); mostre("VIGIA_INSTALADO_OK")' \
    | grep -q '^VIGIA_INSTALADO_OK$'

echo "==> Atualizando a árvore-fonte do servidor após a validação"
if [[ -d "$FONTE_SERVIDOR" ]]; then
    DONO="${SUDO_USER:-rafael}"
    GRUPO="$(id -gn "$DONO")"
    while IFS= read -r relativo; do
        origem="$RAIZ/$relativo"
        destino="$FONTE_SERVIDOR/$relativo"
        mkdir -p "$(dirname "$destino")"
        install -m 0644 -o "$DONO" -g "$GRUPO" "$origem" "$destino"
    done <<'ARQUIVOS'
Makefile
README.md
README.en.md
bibs/bibf/vigia.fé
bibs/bibf/vigia/LEIA-ME.md
bibs/bibf/correio.fé
bibs/bibf/correio/LEIA-ME.md
bibs/bibf/pulso/LEIA-ME.md
docs/ARQUITETURA-DO-ECOSSISTEMA.md
docs/PLANEJAMENTO-SEGURANCA-E-TELEMETRIA.md
testes/bibf/teste_vigia.fé
testes/bibf/teste_correio.fé
testes/bibc/teste_correio_vigia.fé
ARQUIVOS
fi

PUBLICANDO=0
echo "Vigia publicado e validado. Cópia de segurança: $COPIA"
echo "Correio: limites de conexão agora usam uma única instância do Vigia."
