#!/usr/bin/env bash

# Publicador do SLS 0.1.0. Atualiza exclusivamente o núcleo Santafé, seu manual
# e o executor WebAssembly. Nenhum serviço Santafé ou Pão do Café é reiniciado.

set -Eeuo pipefail

MODO="${1:-publicar}"
PACOTE="/tmp/santafe-sls-0.1.0.tar.gz"
PACOTE_SHA256="56aeef3f2d3c52bfb9eda8a3cea80d4930714fb8643f1d1a939462289ec53e49"
RAIZ="${SANTAFE_RAIZ:-/home/rafael/santafe-fonte}"
MANUAL_PUBLICO="/var/www/santafé.dev.br/estático/manual/index.html"
WASM_PUBLICO_JS="/var/www/santafé.dev.br/estático/wasm/santafe.js"
WASM_PUBLICO_BINARIO="/var/www/santafé.dev.br/estático/wasm/santafe.wasm"
URL_MANUAL="https://xn--santaf-gva.dev.br/est%C3%A1tico/manual/index.html"
TRABALHO=""
COPIA=""
ALTEROU=0
CRIADOS=()

NOVOS=(
    'ferramentas/sls/sls.fé|0644'
    'ferramentas/sls/santafé-sls|0755'
    'testes/bibf/teste_json.fé|0644'
    'testes/integracao/testar_sls.py|0755'
    'docs/SLS.md|0644'
    'operação/aplicar-sls-0.1.0.py|0755'
)

limpe_trabalho() {
    if [[ -n "$TRABALHO" && "$TRABALHO" == /tmp/santafe-sls.* ]]; then
        rm -rf -- "$TRABALHO"
    fi
}

restaure() {
    local codigo="$1" linha="$2"
    trap - ERR
    set +e
    echo "ERRO: publicação do SLS interrompida na linha ${linha} (código ${codigo})." >&2
    if [[ "$ALTEROU" -eq 1 && -n "$COPIA" && -f "$COPIA/antes.tar.gz" ]]; then
        tar -xzf "$COPIA/antes.tar.gz" -C /
        for item in "${CRIADOS[@]}"; do
            rm -f -- "$item"
        done
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

for comando in cmp cp curl dirname install make mktemp python3 sha256sum tar; do
    command -v "$comando" >/dev/null 2>&1 || {
        echo "Comando obrigatório ausente: $comando" >&2
        exit 1
    }
done
[[ -d "$RAIZ/src" && -f "$RAIZ/Makefile" ]] || {
    echo "Fonte Santafé não localizado em $RAIZ." >&2
    exit 1
}
[[ -f "$PACOTE" ]] || { echo "Pacote ausente: $PACOTE" >&2; exit 1; }
echo "$PACOTE_SHA256  $PACOTE" | sha256sum -c -

TRABALHO="$(mktemp -d /tmp/santafe-sls.XXXXXX)"
mkdir -p "$TRABALHO/pacote" "$TRABALHO/construcao"
tar -xzf "$PACOTE" -C "$TRABALHO/pacote"

for item in "${NOVOS[@]}"; do
    IFS='|' read -r caminho modo <<< "$item"
    [[ -f "$TRABALHO/pacote/$caminho" ]] || {
        echo "Arquivo ausente no pacote: $caminho" >&2
        exit 1
    }
done

instale_novos_no_fonte() {
    local destino="$1" proprietario="$2" grupo="$3" item caminho modo alvo diretorio
    for item in "${NOVOS[@]}"; do
        IFS='|' read -r caminho modo <<< "$item"
        alvo="$destino/$caminho"
        diretorio="$(dirname -- "$alvo")"
        mkdir -p -- "$diretorio"
        install -o "$proprietario" -g "$grupo" -m "$modo" \
            "$TRABALHO/pacote/$caminho" "$alvo"
    done
}

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

echo "==> Montando e validando o SLS em árvore isolada"
cp -a "$RAIZ/." "$TRABALHO/construcao/"
python3 "$TRABALHO/pacote/operação/aplicar-sls-0.1.0.py" "$TRABALHO/construcao"
instale_novos_no_fonte "$TRABALHO/construcao" "$(id -un)" "$(id -gn)"

make -C "$TRABALHO/construcao/src" clean >/dev/null
make -C "$TRABALHO/construcao" cbin
"$TRABALHO/construcao/src/santafé" "$TRABALHO/construcao/testes/bibf/teste_json.fé"
python3 "$TRABALHO/construcao/testes/integracao/testar_sls.py"
python3 "$TRABALHO/construcao/site-sfdev/validar-manual.py" \
    "$TRABALHO/construcao/site-sfdev/manual.html" \
    --fonte "$TRABALHO/construcao" \
    --api-fe "$TRABALHO/construcao/docs/API-PUBLICA-FE.tsv" \
    --compilador "$TRABALHO/construcao/src/santafec"

echo "==> Recompilando o executor WebAssembly"
prepare_emscripten
(
    cd "$TRABALHO/construcao/src"
    ./emscripten.sh
)
[[ -s "$TRABALHO/construcao/src/santafe.js" ]]
[[ -s "$TRABALHO/construcao/src/santafe.wasm" ]]

if [[ "$MODO" == "--preflight" ]]; then
    echo "Pré-validação do SLS concluída; nenhuma instalação foi alterada."
    exit 0
fi

COPIA="/var/backups/santafe-sls-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$COPIA"
itens_copia=(
    "$RAIZ/Makefile"
    "$RAIZ/.gitignore"
    "$RAIZ/src/lua_cjson.c"
    "$RAIZ/testar.sh"
    "$RAIZ/CHANGELOG.md"
    "$RAIZ/README.md"
    "$RAIZ/README.en.md"
    "$RAIZ/site-sfdev/manual.html"
    "$RAIZ/ferramentas/sls/sls.fé"
    "$RAIZ/ferramentas/sls/santafé-sls"
    "$RAIZ/testes/bibf/teste_json.fé"
    "$RAIZ/testes/integracao/testar_sls.py"
    "$RAIZ/docs/SLS.md"
    "$RAIZ/operação/aplicar-sls-0.1.0.py"
    "$RAIZ/src/santafé"
    "$RAIZ/src/santafec"
    "$RAIZ/src/santafé-sls"
    "$RAIZ/src/liblua.a"
    /usr/local/bin/santafé
    /usr/local/bin/santafec
    /usr/local/bin/santafe
    /usr/local/bin/santafé-sls
    /usr/local/lib/liblua.a
    /usr/local/share/santafé/1.0/ferramentas/sls.fé
    "$MANUAL_PUBLICO"
    "$WASM_PUBLICO_JS"
    "$WASM_PUBLICO_BINARIO"
)
itens_existentes=()
for item in "${itens_copia[@]}"; do
    if [[ -e "$item" || -L "$item" ]]; then
        itens_existentes+=("$item")
    else
        CRIADOS+=("$item")
    fi
done
tar -czf "$COPIA/antes.tar.gz" "${itens_existentes[@]}"

echo "==> Instalando o SLS, núcleo e documentação"
ALTEROU=1
python3 "$TRABALHO/pacote/operação/aplicar-sls-0.1.0.py" "$RAIZ"
instale_novos_no_fonte "$RAIZ" rafael rafael

install -o root -g root -m 0755 "$TRABALHO/construcao/src/santafé" /usr/local/bin/santafé
install -o root -g root -m 0755 "$TRABALHO/construcao/src/santafec" /usr/local/bin/santafec
install -o root -g root -m 0755 "$TRABALHO/construcao/src/santafé-sls" /usr/local/bin/santafé-sls
ln -sfn /usr/local/bin/santafé /usr/local/bin/santafe
install -o root -g root -m 0644 "$TRABALHO/construcao/src/liblua.a" /usr/local/lib/liblua.a
install -D -o root -g root -m 0644 "$RAIZ/ferramentas/sls/sls.fé" \
    /usr/local/share/santafé/1.0/ferramentas/sls.fé
install -o root -g www-data -m 0644 "$RAIZ/site-sfdev/manual.html" "$MANUAL_PUBLICO"
install -o root -g www-data -m 0644 "$TRABALHO/construcao/src/santafe.js" "$WASM_PUBLICO_JS"
install -o root -g www-data -m 0644 "$TRABALHO/construcao/src/santafe.wasm" "$WASM_PUBLICO_BINARIO"
install -o rafael -g rafael -m 0755 "$TRABALHO/construcao/src/santafé" "$RAIZ/src/santafé"
install -o rafael -g rafael -m 0755 "$TRABALHO/construcao/src/santafec" "$RAIZ/src/santafec"
install -o rafael -g rafael -m 0755 "$TRABALHO/construcao/src/santafé-sls" "$RAIZ/src/santafé-sls"
install -o rafael -g rafael -m 0644 "$TRABALHO/construcao/src/liblua.a" "$RAIZ/src/liblua.a"

echo "==> Validando a instalação publicada"
/usr/local/bin/santafé "$RAIZ/testes/bibf/teste_json.fé"
python3 "$RAIZ/testes/integracao/testar_sls.py"
printf '' | /usr/local/bin/santafé-sls
python3 "$RAIZ/site-sfdev/validar-manual.py" "$MANUAL_PUBLICO" \
    --fonte "$RAIZ" --api-fe "$RAIZ/docs/API-PUBLICA-FE.tsv" \
    --compilador /usr/local/bin/santafec
cmp -s "$MANUAL_PUBLICO" "$RAIZ/site-sfdev/manual.html"
curl -fsSL --max-time 20 "$URL_MANUAL?v=$PACOTE_SHA256" \
    -o "$TRABALHO/manual-publicado.html"
cmp -s "$MANUAL_PUBLICO" "$TRABALHO/manual-publicado.html"

ALTEROU=0
echo "SLS 0.1.0 publicado e validado. Cópia de segurança: $COPIA"
echo "Comando local: santafé-sls (LSP por stdin/stdout; diagnóstico sintático)."
echo "Nenhum serviço Santafé ou Pão do Café foi reiniciado."
