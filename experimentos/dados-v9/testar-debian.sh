#!/usr/bin/env bash
# Executado como usuário comum, exclusivamente no diretório de laboratório.
set -euo pipefail
cd "$(dirname "$0")/../.."
test -f .laboratorio-dados9
export PATH="/opt/emsdk/node/24.19.0_64bit/bin:$PATH"
export SANTAFE_ESTAVEL=/usr/local/bin/santafé
export SANTAFE_DADOS7=/tmp/santafe-dados7.1S7FpWIE/arvore/src/santafé
mkdir -p evidencias
python3 experimentos/dados-v3/conferir-fontes.py
bash experimentos/dados-v3/construir.sh > evidencias/dados9-construcao.log 2>&1
make -C ferramentas/sls CFLAGS='-O2 -Wall -Wextra -DSANTAFE_DADOS_EXPERIMENTAL -DLUA_USE_APICHECK'
make -C ferramentas/pacotes CFLAGS='-O2 -Wall -Wextra -DSANTAFE_DADOS_EXPERIMENTAL -DLUA_USE_APICHECK'
python3 experimentos/dados-v9/testar.py
python3 experimentos/dados-v5/testar-aplicativos.py > evidencias/dados9-aplicativos.log 2>&1
(
 source /opt/emsdk/emsdk_env.sh
 export EM_CACHE=/tmp/santafe-dados3.FbzAgzGF/cache-emscripten
 bash experimentos/dados-v7/construir-wasm.sh
) > evidencias/dados9-wasm.log 2>&1
printf '%s\n' 'DADOS9_DEBIAN_E_WASM_OK'
