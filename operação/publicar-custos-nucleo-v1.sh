#!/usr/bin/env bash

set -Eeuo pipefail

MODO="${1:-publicar}"
PACOTE="/tmp/santafe-custos-nucleo-v1.tar.gz"
PACOTE_SHA256="092f60ac50fea13deed035321645f712eda24098c0b45006040a61f3272d6578"
RAIZ="/home/rafael/santafe-fonte"
DESTINO_BIBF="/usr/local/share/santafé/1.0/bibf"
DESTINO_BIBC="/usr/local/lib/santafé/1.0/bibc"
MANUAL_PUBLICO="/var/www/santafé.dev.br/estático/manual/index.html"
WASM_PUBLICO_JS="/var/www/santafé.dev.br/estático/wasm/santafe.js"
WASM_PUBLICO_BINARIO="/var/www/santafé.dev.br/estático/wasm/santafe.wasm"
URL_MANUAL="https://xn--santaf-gva.dev.br/est%C3%A1tico/manual/index.html"

MAPA=(
    'src/lbaselib.c|src/lbaselib.c|0644'
    'src/lstrlib.c|src/lstrlib.c|0644'
    'src/ltablib.c|src/ltablib.c|0644'
    'testes/bibf/teste_colar.fé|testes/bibf/teste_colar.fé|0644'
    'site-sfdev/manual.html|site-sfdev/manual.html|0644'
)

SERVICOS=(
    sfdev.service
    correio-recebedor.service
    correio-agencia.service
    correio-imap.service
    carteiro.service
    nomes-autoridade.service
)
TEMPORIZADORES=(correio-envios.timer)
SERVICOS_ATIVOS=()
TEMPORIZADORES_ATIVOS=()
TRABALHO=""
COPIA=""
ALTEROU=0

limpe_trabalho() {
    if [[ -n "$TRABALHO" && "$TRABALHO" == /tmp/santafe-custos-nucleo.* ]]; then
        rm -rf -- "$TRABALHO"
    fi
}

pare_componentes() {
    local unidade
    systemctl stop correio-envios.service >/dev/null 2>&1 || true
    for unidade in "${TEMPORIZADORES_ATIVOS[@]}"; do
        systemctl stop "$unidade" || true
    done
    for unidade in "${SERVICOS_ATIVOS[@]}"; do
        systemctl stop "$unidade" || true
    done
}

inicie_componentes() {
    local unidade
    for unidade in "${SERVICOS_ATIVOS[@]}"; do
        systemctl start "$unidade"
    done
    for unidade in "${TEMPORIZADORES_ATIVOS[@]}"; do
        systemctl start "$unidade"
    done
}

restaure() {
    local codigo="$1" linha="$2"
    trap - ERR
    set +e
    echo "ERRO: publicação do núcleo interrompida na linha ${linha} (código ${codigo})." >&2
    if [[ "$ALTEROU" -eq 1 && -n "$COPIA" && -f "$COPIA/antes.tar.gz" ]]; then
        pare_componentes
        tar -xzf "$COPIA/antes.tar.gz" -C /
        inicie_componentes
        echo "Versão anterior restaurada. Cópia de segurança: $COPIA" >&2
    fi
    limpe_trabalho
    exit "$codigo"
}

trap 'restaure "$?" "$LINENO"' ERR
trap 'limpe_trabalho' EXIT

if [[ "$MODO" != "publicar" && "$MODO" != "--preflight" ]]; then
    echo "Uso: $0 [--preflight]" >&2
    exit 2
fi
if [[ "$MODO" == "publicar" && "$EUID" -ne 0 ]]; then
    echo "Execute com sudo." >&2
    exit 1
fi

for comando in cmp cp curl install make mktemp python3 sha256sum systemctl tar; do
    command -v "$comando" >/dev/null 2>&1 || {
        echo "Comando obrigatório ausente: $comando" >&2
        exit 1
    }
done
[[ -f "$PACOTE" ]] || { echo "Pacote ausente: $PACOTE" >&2; exit 1; }
echo "$PACOTE_SHA256  $PACOTE" | sha256sum -c -
[[ -d "$RAIZ/src" && -f "$RAIZ/Makefile" ]] || {
    echo "Fonte Santafé não localizado em $RAIZ." >&2
    exit 1
}

TRABALHO="$(mktemp -d /tmp/santafe-custos-nucleo.XXXXXX)"
mkdir -p "$TRABALHO/pacote" "$TRABALHO/construcao"
tar -xzf "$PACOTE" -C "$TRABALHO/pacote"

for entrada in "${MAPA[@]}"; do
    IFS='|' read -r origem destino modo <<< "$entrada"
    [[ -f "$TRABALHO/pacote/$origem" ]] || {
        echo "Arquivo ausente no pacote: $origem" >&2
        exit 1
    }
done

cp -a "$RAIZ/." "$TRABALHO/construcao/"
for entrada in "${MAPA[@]}"; do
    IFS='|' read -r origem destino modo <<< "$entrada"
    install -D -m "$modo" "$TRABALHO/pacote/$origem" \
        "$TRABALHO/construcao/$destino"
done

echo "==> Recompilando e validando o núcleo em árvore isolada"
make -C "$TRABALHO/construcao/src" clean >/dev/null
make -C "$TRABALHO/construcao" cbin
"$TRABALHO/construcao/src/santafé" \
    "$TRABALHO/construcao/testes/bibf/teste_colar.fé"
python3 "$TRABALHO/construcao/site-sfdev/validar-manual.py" \
    "$TRABALHO/construcao/site-sfdev/manual.html" \
    --fonte "$TRABALHO/construcao" \
    --api-fe "$TRABALHO/construcao/docs/API-PUBLICA-FE.tsv" \
    --compilador "$TRABALHO/construcao/src/santafec"

prepare_emscripten() {
    local candidato usuario="${SUDO_USER:-rafael}"
    if command -v emcc >/dev/null 2>&1; then return 0; fi
    for candidato in "/home/$usuario/emsdk/emsdk_env.sh" "/root/emsdk/emsdk_env.sh" "/opt/emsdk/emsdk_env.sh"; do
        if [[ -f "$candidato" ]]; then
            # shellcheck disable=SC1090
            source "$candidato"
            command -v emcc >/dev/null 2>&1 && return 0
        fi
    done
    echo "Emscripten (emcc) não encontrado; a publicação exige atualizar o executor WebAssembly." >&2
    return 1
}

echo "==> Recompilando o executor WebAssembly"
prepare_emscripten
(
    cd "$TRABALHO/construcao/src"
    ./emscripten.sh
)
[[ -s "$TRABALHO/construcao/src/santafe.js" ]]
[[ -s "$TRABALHO/construcao/src/santafe.wasm" ]]
LC_ALL=C grep -aFq 'maiorÍndice' "$TRABALHO/construcao/src/santafe.wasm"

if [[ "$MODO" == "--preflight" ]]; then
    echo "Pré-validação concluída; nenhuma instalação foi alterada."
    exit 0
fi

for unidade in "${SERVICOS[@]}"; do
    if systemctl is-active --quiet "$unidade"; then
        SERVICOS_ATIVOS+=("$unidade")
    fi
done
for unidade in "${TEMPORIZADORES[@]}"; do
    if systemctl is-active --quiet "$unidade"; then
        TEMPORIZADORES_ATIVOS+=("$unidade")
    fi
done

COPIA="/var/backups/santafe-custos-nucleo-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$COPIA"
itens_copia=(
    /usr/local/bin/santafé
    /usr/local/bin/santafec
    /usr/local/bin/santafe
    /usr/local/lib/liblua.a
    "$MANUAL_PUBLICO"
    "$WASM_PUBLICO_JS"
    "$WASM_PUBLICO_BINARIO"
)
for entrada in "${MAPA[@]}"; do
    IFS='|' read -r origem destino modo <<< "$entrada"
    itens_copia+=("$RAIZ/$destino")
done
tar -czf "$COPIA/antes.tar.gz" "${itens_copia[@]}"

echo "==> Instalando núcleo, manual e WebAssembly"
pare_componentes
ALTEROU=1
for entrada in "${MAPA[@]}"; do
    IFS='|' read -r origem destino modo <<< "$entrada"
    install -D -o rafael -g rafael -m "$modo" "$TRABALHO/pacote/$origem" \
        "$RAIZ/$destino"
done
install -o root -g root -m 0755 "$TRABALHO/construcao/src/santafé" /usr/local/bin/santafé
install -o root -g root -m 0755 "$TRABALHO/construcao/src/santafec" /usr/local/bin/santafec
ln -sfn /usr/local/bin/santafé /usr/local/bin/santafe
install -o root -g root -m 0644 "$TRABALHO/construcao/src/liblua.a" /usr/local/lib/liblua.a
install -o root -g www-data -m 0644 "$TRABALHO/pacote/site-sfdev/manual.html" "$MANUAL_PUBLICO"
install -o root -g www-data -m 0644 "$TRABALHO/construcao/src/santafe.js" "$WASM_PUBLICO_JS"
install -o root -g www-data -m 0644 "$TRABALHO/construcao/src/santafe.wasm" "$WASM_PUBLICO_BINARIO"
install -o rafael -g rafael -m 0755 "$TRABALHO/construcao/src/santafé" "$RAIZ/src/santafé"
install -o rafael -g rafael -m 0755 "$TRABALHO/construcao/src/santafec" "$RAIZ/src/santafec"
install -o rafael -g rafael -m 0644 "$TRABALHO/construcao/src/liblua.a" "$RAIZ/src/liblua.a"

echo "==> Reiniciando os serviços que estavam ativos"
inicie_componentes
for unidade in "${SERVICOS_ATIVOS[@]}"; do
    systemctl is-active --quiet "$unidade"
done
for unidade in "${TEMPORIZADORES_ATIVOS[@]}"; do
    systemctl is-active --quiet "$unidade"
done

echo "==> Validando a instalação publicada"
env GSETTINGS_BACKEND=memory \
    LUA_PATH="$DESTINO_BIBF/?.fé;$DESTINO_BIBF/?/?.fé;;" \
    LUA_CPATH="$DESTINO_BIBC/?.so;;" \
    /usr/local/bin/santafé "$RAIZ/testes/bibf/teste_colar.fé"
python3 "$RAIZ/site-sfdev/validar-manual.py" "$MANUAL_PUBLICO" \
    --fonte "$RAIZ" --api-fe "$RAIZ/docs/API-PUBLICA-FE.tsv" \
    --compilador /usr/local/bin/santafec
cmp -s "$MANUAL_PUBLICO" "$RAIZ/site-sfdev/manual.html"
LC_ALL=C grep -aFq 'maiorÍndice' "$WASM_PUBLICO_BINARIO"
curl -fsSL --max-time 20 "$URL_MANUAL?v=$PACOTE_SHA256" \
    -o "$TRABALHO/manual-publicado.html"
cmp -s "$MANUAL_PUBLICO" "$TRABALHO/manual-publicado.html"

ALTEROU=0
echo "Custos e limites do núcleo publicados e validados."
echo "tamanho(tabela) acompanha #; maiorÍndice é o nome principal; descompacte limita 64 MiB por padrão."
echo "Cópia de segurança: $COPIA"
