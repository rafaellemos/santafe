#!/usr/bin/env bash

set -Eeuo pipefail

MODO="${1:-publicar}"
PACOTE="/tmp/santafe-grafemas-v1.tar.gz"
PACOTE_SHA256="c400d9f5ab2e6a06a75550b024008494066750b64f39301bf3c1280b5a03ac0c"
RAIZ="/home/rafael/santafe-fonte"
DESTINO_BIBF="/usr/local/share/santafé/1.0/bibf"
DESTINO_BIBC="/usr/local/lib/santafé/1.0/bibc"
MANUAL_PUBLICO="/var/www/santafé.dev.br/estático/manual/index.html"
WASM_PUBLICO_JS="/var/www/santafé.dev.br/estático/wasm/santafe.js"
WASM_PUBLICO_BINARIO="/var/www/santafé.dev.br/estático/wasm/santafe.wasm"
URL_MANUAL="https://xn--santaf-gva.dev.br/est%C3%A1tico/manual/index.html"

MAPA=(
    'src/lunicode.c|src/lunicode.c|0644'
    'src/lunicode.h|src/lunicode.h|0644'
    'src/lunicode-ranges.h|src/lunicode-ranges.h|0644'
    'src/lstrlib.c|src/lstrlib.c|0644'
    'src/lbaselib.c|src/lbaselib.c|0644'
    'src/Makefile|src/Makefile|0644'
    'src/emscripten.sh|src/emscripten.sh|0755'
    'testes/bibf/teste_colar.fé|testes/bibf/teste_colar.fé|0644'
    'exemplos/09-boas-vindas.fé|exemplos/09-boas-vindas.fé|0644'
    'README.md|README.md|0644'
    'README.en.md|README.en.md|0644'
    'CHANGELOG.md|CHANGELOG.md|0644'
    'site-sfdev/manual.html|site-sfdev/manual.html|0644'
)

SERVICOS=(
    sfdev.service
    paodocafe.service
    correio-recebedor.service
    correio-agencia.service
    correio-imap.service
    carteiro.service
    carteiro-paodocafe.service
    nomes-autoridade.service
)
TEMPORIZADORES=(
    correio-envios.timer
    correio-envios-paodocafe.timer
)
SERVICOS_ATIVOS=()
TEMPORIZADORES_ATIVOS=()
TRABALHO=""
COPIA=""
ALTEROU=0
NOVOS=()

limpe_trabalho() {
    if [[ -n "$TRABALHO" && "$TRABALHO" == /tmp/santafe-grafemas.* ]]; then
        rm -rf -- "$TRABALHO"
    fi
}

pare_componentes() {
    local unidade
    systemctl stop correio-envios.service correio-envios-paodocafe.service \
        >/dev/null 2>&1 || true
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
    local codigo="$1" linha="$2" item
    trap - ERR
    set +e
    echo "ERRO: publicação de grafemas interrompida na linha ${linha} (código ${codigo})." >&2
    if [[ "$ALTEROU" -eq 1 && -n "$COPIA" && -f "$COPIA/antes.tar.gz" ]]; then
        pare_componentes
        tar -xzf "$COPIA/antes.tar.gz" -C /
        for item in "${NOVOS[@]}"; do
            rm -f -- "$item"
        done
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

for comando in bash cmp cp curl find grep install make mktemp python3 sha256sum \
    systemctl tar; do
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

TRABALHO="$(mktemp -d /tmp/santafe-grafemas.XXXXXX)"
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

echo "==> Compilando o núcleo em árvore isolada"
make -C "$TRABALHO/construcao/src" clean >/dev/null
make -C "$TRABALHO/construcao" cbin

echo "==> Validando grafemas, octetos e o manual"
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
LC_ALL=C grep -aFq 'octetos' "$TRABALHO/construcao/src/santafe.wasm"

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

COPIA="/var/backups/santafe-grafemas-$(date +%Y%m%d-%H%M%S)"
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
    alvo="$RAIZ/$destino"
    if [[ -e "$alvo" || -L "$alvo" ]]; then
        itens_copia+=("$alvo")
    else
        NOVOS+=("$alvo")
    fi
done
tar -czf "$COPIA/antes.tar.gz" "${itens_copia[@]}"

echo "==> Instalando núcleo, documentação e WebAssembly"
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
LC_ALL=C grep -aFq 'octetos' "$WASM_PUBLICO_BINARIO"
curl -fsSL --max-time 20 "$URL_MANUAL?v=$PACOTE_SHA256" \
    -o "$TRABALHO/manual-publicado.html"
cmp -s "$MANUAL_PUBLICO" "$TRABALHO/manual-publicado.html"

ALTEROU=0
echo "Grafemas e octetos publicados e validados."
echo "tamanho/colar.tamanho contam grafemas; octetos e # contam bytes."
echo "Cópia de segurança: $COPIA"
