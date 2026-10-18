#!/usr/bin/env bash

set -Eeuo pipefail

DESTINO="/opt/emsdk"

if [[ "$EUID" -ne 0 ]]; then
    echo "Execute com sudo." >&2
    exit 1
fi

for comando in apt-get python3; do
    command -v "$comando" >/dev/null 2>&1 || {
        echo "Comando obrigatório ausente: $comando" >&2
        exit 1
    }
done

if [[ -x "$DESTINO/upstream/emscripten/emcc" ]]; then
    # shellcheck disable=SC1091
    source "$DESTINO/emsdk_env.sh" >/dev/null
    emcc --version
    echo "Emscripten já está pronto em $DESTINO."
    exit 0
fi

if [[ -e "$DESTINO" && ! -d "$DESTINO/.git" ]]; then
    echo "O destino $DESTINO existe e não é um clone do emsdk; não foi alterado." >&2
    exit 1
fi

echo "==> Instalando pré-requisitos do compilador WebAssembly"
apt-get update
apt-get install -y git python3 ca-certificates

if [[ ! -d "$DESTINO/.git" ]]; then
    echo "==> Baixando o SDK oficial Emscripten"
    git clone https://github.com/emscripten-core/emsdk.git "$DESTINO"
fi

echo "==> Instalando e ativando a versão estável do Emscripten"
"$DESTINO/emsdk" install latest
"$DESTINO/emsdk" activate latest

# shellcheck disable=SC1091
source "$DESTINO/emsdk_env.sh" >/dev/null
emcc --version
echo "Emscripten pronto em $DESTINO."
