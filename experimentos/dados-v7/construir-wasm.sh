#!/usr/bin/env bash
# Usar com emcc e node no PATH. Só cria artefatos na árvore experimental.
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
[[ -f "$root/.laboratorio-dados7" ]] || { echo 'Exige laboratório dados.7.' >&2; exit 2; }
command -v emcc >/dev/null
command -v node >/dev/null
cd "$root/src"
SANTAFE_EXPERIMENTO_DADOS=1 bash emscripten.sh
node "$root/experimentos/dados-v3/testar-wasm.js"
