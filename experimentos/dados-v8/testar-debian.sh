#!/usr/bin/env bash
# Só fontes candidatas e bancos/portas privados; não instala em /usr ou /opt.
set -euo pipefail
cd "$(dirname "$0")/../.."
test -f .laboratorio-dados8
test -n "${SANTAFE_ESTAVEL:-}"
test -n "${SANTAFE_DADOS7:-}"
mkdir -p evidencias
python3 experimentos/dados-v3/conferir-fontes.py
bash experimentos/dados-v3/construir.sh > evidencias/dados8-construcao.log 2>&1
make -C ferramentas/sls CFLAGS='-O2 -Wall -Wextra -DSANTAFE_DADOS_EXPERIMENTAL -DLUA_USE_APICHECK'
make -C ferramentas/pacotes CFLAGS='-O2 -Wall -Wextra -DSANTAFE_DADOS_EXPERIMENTAL -DLUA_USE_APICHECK'
python3 experimentos/dados-v8/testar-colares.py > evidencias/dados8-colares.log 2>&1
python3 experimentos/dados-v8/testar-fontes.py > evidencias/dados8-fontes.log 2>&1
python3 experimentos/dados-v8/testar-sls.py > evidencias/dados8-sls.log 2>&1
python3 experimentos/dados-v7/validar.py > evidencias/dados8-regressao.log 2>&1
python3 experimentos/dados-v5/testar-aplicativos.py > evidencias/dados8-aplicativos.log 2>&1
(
    source /opt/emsdk/emsdk_env.sh
    export EM_CACHE=/tmp/santafe-dados3.FbzAgzGF/cache-emscripten
    bash experimentos/dados-v7/construir-wasm.sh
) > evidencias/dados8-wasm.log 2>&1
printf '%s\n' 'DADOS8_DEBIAN_E_WASM_OK'
