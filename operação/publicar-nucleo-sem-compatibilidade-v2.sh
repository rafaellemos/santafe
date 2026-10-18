#!/usr/bin/env bash

set -Eeuo pipefail

MODO="${1:-publicar}"
PACOTE="/tmp/santafe-nucleo-sem-compatibilidade-v2.tar.gz"
PACOTE_SHA256="8547472e67bfddbe248c83eb6233bfd8809a92a217c9324551267d8e76322cc7"
RAIZ="/home/rafael/santafe-fonte"
DESTINO_BIBF="/usr/local/share/santafé/1.0/bibf"
DESTINO_BIBC="/usr/local/lib/santafé/1.0/bibc"
MANUAL_PUBLICO="/var/www/santafé.dev.br/estático/manual/index.html"
PRISM_PUBLICO="/var/www/santafé.dev.br/estático/js/prism-santafé.js"
WASM_PUBLICO_JS="/var/www/santafé.dev.br/estático/wasm/santafe.js"
WASM_PUBLICO_BINARIO="/var/www/santafé.dev.br/estático/wasm/santafe.wasm"
URL_MANUAL="https://xn--santaf-gva.dev.br/est%C3%A1tico/manual/index.html"

MAPA=(
    'src/Makefile|src/Makefile|0644'
    'src/emscripten.sh|src/emscripten.sh|0755'
    'src/lauxlib.c|src/lauxlib.c|0644'
    'src/lauxlib.h|src/lauxlib.h|0644'
    'src/lbaselib.c|src/lbaselib.c|0644'
    'src/lmathlib.c|src/lmathlib.c|0644'
    'src/loadlib.c|src/loadlib.c|0644'
    'src/lobject.c|src/lobject.c|0644'
    'src/lstrlib.c|src/lstrlib.c|0644'
    'src/ltablib.c|src/ltablib.c|0644'
    'src/lua.h|src/lua.h|0644'
    'src/luaconf.h|src/luaconf.h|0644'
    'include/lauxlib.h|include/lauxlib.h|0644'
    'include/lua.h|include/lua.h|0644'
    'include/luaconf.h|include/luaconf.h|0644'
    'testes/bibf/teste_colar.fé|testes/bibf/teste_colar.fé|0644'
    'testes/bibf/teste_mat.fé|testes/bibf/teste_mat.fé|0644'
    'docs/ARQUITETURA-DO-ECOSSISTEMA.md|docs/ARQUITETURA-DO-ECOSSISTEMA.md|0644'
    'CHANGELOG.md|CHANGELOG.md|0644'
    'site-sfdev/manual.html|site-sfdev/manual.html|0644'
    'site-sfdev/prism-santafé.js|site-sfdev/prism-santafé.js|0644'
    'site-sfdev/validar-manual.py|site-sfdev/validar-manual.py|0755'
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
    if [[ -n "$TRABALHO" && "$TRABALHO" == /tmp/santafe-nucleo-sem-compatibilidade.* ]]; then
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

TRABALHO="$(mktemp -d /tmp/santafe-nucleo-sem-compatibilidade.XXXXXX)"
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

verifique_api_sem_compatibilidade() {
    local interpretador="$1"
    env GSETTINGS_BACKEND=memory \
        LUA_PATH="$DESTINO_BIBF/?.fé;$DESTINO_BIBF/?/?.fé;;" \
        LUA_CPATH="$DESTINO_BIBC/?.so;;" \
        "$interpretador" -e '
            garanta(tabela.maiorN == nulo)
            garanta(mat.arcoTangente2 == nulo)
            garanta(carregueColar == nulo)
            garanta(desempacote == nulo)
            garanta(módulo.módulo == nulo)
            garanta(módulo.verTodos == nulo)
            garanta(módulo.carregadores == nulo)
            garanta(mat.potência(2, 8) == 256)
            mostre("NUCLEO_SEM_COMPATIBILIDADE_OK")
        '
}

echo "==> Recompilando e validando o núcleo em árvore isolada"
make -C "$TRABALHO/construcao/src" clean >/dev/null
make -C "$TRABALHO/construcao" cbin
"$TRABALHO/construcao/src/santafé" \
    "$TRABALHO/construcao/testes/bibf/teste_colar.fé"
"$TRABALHO/construcao/src/santafé" \
    "$TRABALHO/construcao/testes/bibf/teste_mat.fé"
verifique_api_sem_compatibilidade "$TRABALHO/construcao/src/santafé"
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

COPIA="/var/backups/santafe-nucleo-sem-compatibilidade-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$COPIA"
itens_copia=(
    /usr/local/bin/santafé
    /usr/local/bin/santafec
    /usr/local/bin/santafe
    /usr/local/lib/liblua.a
    "$MANUAL_PUBLICO"
    "$PRISM_PUBLICO"
    "$WASM_PUBLICO_JS"
    "$WASM_PUBLICO_BINARIO"
)
for entrada in "${MAPA[@]}"; do
    IFS='|' read -r origem destino modo <<< "$entrada"
    itens_copia+=("$RAIZ/$destino")
done
itens_existentes=()
for item in "${itens_copia[@]}"; do
    [[ -e "$item" || -L "$item" ]] && itens_existentes+=("$item")
done
tar -czf "$COPIA/antes.tar.gz" "${itens_existentes[@]}"

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
install -o root -g www-data -m 0644 "$TRABALHO/pacote/site-sfdev/prism-santafé.js" "$PRISM_PUBLICO"
install -o root -g www-data -m 0644 "$TRABALHO/construcao/src/santafe.js" "$WASM_PUBLICO_JS"
install -o root -g www-data -m 0644 "$TRABALHO/construcao/src/santafe.wasm" "$WASM_PUBLICO_BINARIO"
install -o rafael -g rafael -m 0755 "$TRABALHO/construcao/src/santafé" "$RAIZ/src/santafé"
install -o rafael -g rafael -m 0755 "$TRABALHO/construcao/src/santafec" "$RAIZ/src/santafec"
install -o rafael -g rafael -m 0644 "$TRABALHO/construcao/src/liblua.a" "$RAIZ/src/liblua.a"

echo "==> Reiniciando os serviços Santafé que estavam ativos"
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
env GSETTINGS_BACKEND=memory \
    LUA_PATH="$DESTINO_BIBF/?.fé;$DESTINO_BIBF/?/?.fé;;" \
    LUA_CPATH="$DESTINO_BIBC/?.so;;" \
    /usr/local/bin/santafé "$RAIZ/testes/bibf/teste_mat.fé"
verifique_api_sem_compatibilidade /usr/local/bin/santafé
python3 "$RAIZ/site-sfdev/validar-manual.py" "$MANUAL_PUBLICO" \
    --fonte "$RAIZ" --api-fe "$RAIZ/docs/API-PUBLICA-FE.tsv" \
    --compilador /usr/local/bin/santafec
cmp -s "$MANUAL_PUBLICO" "$RAIZ/site-sfdev/manual.html"
curl -fsSL --max-time 20 "$URL_MANUAL?v=$PACOTE_SHA256" \
    -o "$TRABALHO/manual-publicado.html"
cmp -s "$MANUAL_PUBLICO" "$TRABALHO/manual-publicado.html"

ALTEROU=0
echo "Núcleo sem modos de compatibilidade publicado e validado."
echo "Removidos: maiorN, arcoTangente2, carregueColar, desempacote global e módulo legado."
echo "Mantidos como API Santafé: potência, log10, hiperbólicas, decompõe2 e recompõe2."
echo "Pão do Café não foi reiniciado. Cópia de segurança: $COPIA"
