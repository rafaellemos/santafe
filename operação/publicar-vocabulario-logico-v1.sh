#!/usr/bin/env bash

set -Eeuo pipefail

MODO="${1:-publicar}"
PACOTE="/tmp/santafe-vocabulario-logico-20261002.tar.gz"
PACOTE_SHA256="338182341d7767063a2c6ddcf5bbcff7bfe1ac0a62d6de05cf33f62b1b612acb"
RAIZ="/home/rafael/santafe-fonte"
DESTINO_BIBF="/usr/local/share/santafé/1.0/bibf"
DESTINO_BIBC="/usr/local/lib/santafé/1.0/bibc"
MANUAL_PUBLICO="/var/www/santafé.dev.br/estático/manual/index.html"
WASM_PUBLICO_JS="/var/www/santafé.dev.br/estático/wasm/santafe.js"
WASM_PUBLICO_BINARIO="/var/www/santafé.dev.br/estático/wasm/santafe.wasm"

SERVICOS=(
    nomes-autoridade.service
    sfdev.service
    paodocafe.service
    correio-recebedor.service
    correio-agencia.service
    correio-imap.service
    carteiro.service
    carteiro-paodocafe.service
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

mapa_do_contrato=(
    'src-llex.h|src/llex.h'
    'src-llex.c|src/llex.c'
    'src-lparser.c|src/lparser.c'
    'src-ldebug.c|src/ldebug.c'
    'src-lapi.c|src/lapi.c'
    'src-lstrlib.c|src/lstrlib.c'
    'src-ltm.c|src/ltm.c'
    'src-lua-cjson.c|src/lua_cjson.c'
    'pulso.fe|bibs/bibf/pulso.fé'
    'tomada-options.c|bibs/bibc/tomada/options.c'
    'rede.c|bibs/bibc/rede/rede.c'
    'teste-pulso.fe|testes/bibf/teste_pulso.fé'
    'teste-linguagem.fe|testes/bibf/teste_linguagem.fé'
    'santafe.js|src/santafe.js'
    'santafe.wasm|src/santafe.wasm'
    'manual.html|site-sfdev/manual.html'
    'validar-manual.py|site-sfdev/validar-manual.py'
    'json-santafe.svg|site-sfdev/fotos/json-santafe.svg'
)

limpe_trabalho() {
    if [[ -n "$TRABALHO" && "$TRABALHO" == /tmp/santafe-vocabulario-logico.* ]]; then
        rm -rf -- "$TRABALHO"
    fi
}

pare_componentes() {
    local i
    systemctl stop correio-envios.service \
        correio-envios-paodocafe.service >/dev/null 2>&1 || true
    for ((i=${#TEMPORIZADORES_ATIVOS[@]}-1; i>=0; i--)); do
        systemctl stop "${TEMPORIZADORES_ATIVOS[$i]}" || true
    done
    for ((i=${#SERVICOS_ATIVOS[@]}-1; i>=0; i--)); do
        systemctl stop "${SERVICOS_ATIVOS[$i]}" || true
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
    local codigo="$1"
    local linha="$2"
    trap - ERR
    set +e
    echo "ERRO: revisão do vocabulário interrompida na linha ${linha} (código ${codigo})." >&2
    if [[ "$ALTEROU" -eq 1 && -n "$COPIA" && -f "$COPIA/antes.tar.gz" ]]; then
        pare_componentes
        rm -f "$RAIZ/testes/bibf/teste_linguagem.fé"
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

if [[ "$MODO" == "publicar" && "${EUID}" -ne 0 ]]; then
    echo "Execute com sudo." >&2
    exit 1
fi

for comando in make gcc tar sha256sum python3 curl systemctl install ss awk seq; do
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

TRABALHO="$(mktemp -d /tmp/santafe-vocabulario-logico.XXXXXX)"
mkdir -p "$TRABALHO/pacote" "$TRABALHO/construcao"
tar -xzf "$PACOTE" -C "$TRABALHO/pacote"

for item in "${mapa_do_contrato[@]}"; do
    IFS='|' read -r origem destino <<< "$item"
    [[ -f "$TRABALHO/pacote/$origem" ]] || {
        echo "Arquivo ausente no pacote: $origem" >&2
        exit 1
    }
done

cp -a "$RAIZ/." "$TRABALHO/construcao/"
for item in "${mapa_do_contrato[@]}"; do
    IFS='|' read -r origem destino <<< "$item"
    install -D -m 0644 "$TRABALHO/pacote/$origem" \
        "$TRABALHO/construcao/$destino"
done

echo "==> Compilando o núcleo Linux em uma árvore isolada"
make -C "$TRABALHO/construcao/src" clean >/dev/null
make -C "$TRABALHO/construcao" cbin
make -C "$TRABALHO/construcao/bibs/bibc/tomada" clean >/dev/null
make -C "$TRABALHO/construcao/bibs/bibc/tomada"

CAMINHO_F="$TRABALHO/construcao/bibs/bibf/?.fé;$TRABALHO/construcao/bibs/bibf/?/?.fé;;"
CAMINHO_C="$TRABALHO/construcao/bibs/bibc/?/?.so;$DESTINO_BIBC/?.so;;"

echo "==> Validando o contrato novo antes da troca"
env GSETTINGS_BACKEND=memory LUA_PATH="$CAMINHO_F" LUA_CPATH="$CAMINHO_C" \
    "$TRABALHO/construcao/src/santafé" \
    "$TRABALHO/construcao/testes/bibf/teste_linguagem.fé"
env GSETTINGS_BACKEND=memory LUA_PATH="$CAMINHO_F" LUA_CPATH="$CAMINHO_C" \
    "$TRABALHO/construcao/src/santafé" \
    "$TRABALHO/construcao/testes/bibf/teste_pulso.fé"
python3 "$TRABALHO/construcao/site-sfdev/validar-manual.py" \
    "$TRABALHO/construcao/site-sfdev/manual.html" \
    --compilador "$TRABALHO/construcao/src/santafec"
LC_ALL=C grep -aFq 'lógico' "$TRABALHO/pacote/santafe.wasm"
LC_ALL=C grep -aFq '_AMBIENTE' "$TRABALHO/pacote/santafe.wasm"
if LC_ALL=C grep -aEq 'booleano|_ENV' "$TRABALHO/pacote/santafe.wasm"; then
    echo "O executor WASM ainda contém o vocabulário anterior." >&2
    exit 1
fi

if [[ "$MODO" == "--preflight" ]]; then
    echo "Pré-validação Linux concluída; nenhuma instalação foi alterada."
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

COPIA="/var/backups/santafe-vocabulario-logico-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$COPIA"
echo "==> Criando a cópia de segurança"
tar -czf "$COPIA/antes.tar.gz" \
    "$RAIZ" \
    /usr/local/bin/santafé \
    /usr/local/bin/santafec \
    /usr/local/bin/santafe \
    /usr/local/lib/liblua.a \
    "$DESTINO_BIBC/tomada.so" \
    "$DESTINO_BIBF/pulso.fé" \
    "$MANUAL_PUBLICO" \
    "$WASM_PUBLICO_JS" \
    "$WASM_PUBLICO_BINARIO" \
    /var/www/santafé.dev.br/estático/fotos/json-santafe.svg

echo "==> Parando somente os consumidores do interpretador"
pare_componentes
ALTEROU=1

echo "==> Instalando lógico, _AMBIENTE, PULSO e o manual"
for item in "${mapa_do_contrato[@]}"; do
    IFS='|' read -r origem destino <<< "$item"
    install -D -o rafael -g rafael -m 0644 \
        "$TRABALHO/pacote/$origem" "$RAIZ/$destino"
done

install -o root -g root -m 0755 \
    "$TRABALHO/construcao/src/santafé" /usr/local/bin/santafé
install -o root -g root -m 0755 \
    "$TRABALHO/construcao/src/santafec" /usr/local/bin/santafec
ln -sfn /usr/local/bin/santafé /usr/local/bin/santafe
install -o root -g root -m 0644 \
    "$TRABALHO/construcao/src/liblua.a" /usr/local/lib/liblua.a
install -o root -g root -m 0755 \
    "$TRABALHO/construcao/bibs/bibc/tomada/tomada.so" \
    "$DESTINO_BIBC/tomada.so"
install -o root -g root -m 0644 \
    "$TRABALHO/pacote/pulso.fe" "$DESTINO_BIBF/pulso.fé"
install -o root -g www-data -m 0644 \
    "$TRABALHO/pacote/manual.html" "$MANUAL_PUBLICO"
install -o root -g www-data -m 0644 \
    "$TRABALHO/pacote/santafe.js" "$WASM_PUBLICO_JS"
install -o root -g www-data -m 0644 \
    "$TRABALHO/pacote/santafe.wasm" "$WASM_PUBLICO_BINARIO"
install -o root -g www-data -m 0644 \
    "$TRABALHO/pacote/json-santafe.svg" \
    /var/www/santafé.dev.br/estático/fotos/json-santafe.svg

install -o rafael -g rafael -m 0755 \
    "$TRABALHO/construcao/src/santafé" "$RAIZ/src/santafé"
install -o rafael -g rafael -m 0755 \
    "$TRABALHO/construcao/src/santafec" "$RAIZ/src/santafec"
install -o rafael -g rafael -m 0644 \
    "$TRABALHO/construcao/src/liblua.a" "$RAIZ/src/liblua.a"
install -o rafael -g rafael -m 0755 \
    "$TRABALHO/construcao/bibs/bibc/tomada/tomada.so" \
    "$RAIZ/bibs/bibc/tomada/tomada.so"

echo "==> Reiniciando e validando os dois projetos"
inicie_componentes

for unidade in "${SERVICOS_ATIVOS[@]}"; do
    systemctl is-active --quiet "$unidade"
done
for unidade in "${TEMPORIZADORES_ATIVOS[@]}"; do
    systemctl is-active --quiet "$unidade"
done

env GSETTINGS_BACKEND=memory \
    LUA_PATH="$DESTINO_BIBF/?.fé;$DESTINO_BIBF/?/?.fé;;" \
    LUA_CPATH="$DESTINO_BIBC/?.so;;" \
    /usr/local/bin/santafé "$RAIZ/testes/bibf/teste_linguagem.fé"
env GSETTINGS_BACKEND=memory \
    LUA_PATH="$DESTINO_BIBF/?.fé;$DESTINO_BIBF/?/?.fé;;" \
    LUA_CPATH="$DESTINO_BIBC/?.so;;" \
    /usr/local/bin/santafé "$RAIZ/testes/bibf/teste_pulso.fé"
python3 "$RAIZ/site-sfdev/validar-manual.py" "$MANUAL_PUBLICO" \
    --compilador /usr/local/bin/santafec
LC_ALL=C grep -aFq 'lógico' "$WASM_PUBLICO_BINARIO"
LC_ALL=C grep -aFq '_AMBIENTE' "$WASM_PUBLICO_BINARIO"
if LC_ALL=C grep -aEq 'booleano|_ENV' "$WASM_PUBLICO_BINARIO"; then
    echo "O executor WASM público ainda contém o vocabulário anterior." >&2
    exit 1
fi

confira_http() {
    local url="$1"
    local tentativa
    for tentativa in $(seq 1 30); do
        if curl -fsS --max-time 2 "$url" >/dev/null; then return 0; fi
        sleep 1
    done
    echo "Serviço HTTP não respondeu: $url" >&2
    return 1
}

confira_http http://127.0.0.1:7000/
confira_http http://127.0.0.1:7100/carteiro/estado
confira_http http://127.0.0.1:7101/carteiro/estado
confira_http http://127.0.0.1:7200/

for porta in 25 465 587 993; do
    ss -lnt | awk -v porta=":${porta}" '$4 ~ porta "$" { achou=1 } END { exit !achou }'
done

ALTEROU=0
echo "Revisão do vocabulário publicada e validada."
echo "tipo(verdadeiro): lógico; ambiente léxico: _AMBIENTE."
echo "mat.tipo permanece inteiro/flutuante; PULSO preserva valores lógicos."
echo "Santafé e Pão do Café reiniciados sem compartilhar fontes."
echo "Cópia de segurança: $COPIA"
