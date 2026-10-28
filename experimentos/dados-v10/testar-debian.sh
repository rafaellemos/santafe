#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
test -f .laboratorio-dados10
export PATH="/opt/emsdk/node/24.19.0_64bit/bin:$PATH"
export SANTAFE_ESTAVEL=/usr/local/bin/santafé
export SANTAFE_DADOS7=/tmp/santafe-dados7.1S7FpWIE/arvore/src/santafé
mkdir -p evidencias
python3 experimentos/dados-v3/conferir-fontes.py
bash experimentos/dados-v3/construir.sh > evidencias/dados10-construcao.log 2>&1
make -C ferramentas/sls CFLAGS='-O2 -Wall -Wextra -DSANTAFE_DADOS_EXPERIMENTAL -DLUA_USE_APICHECK' > evidencias/dados10-helper-sls.log 2>&1
make -C ferramentas/pacotes CFLAGS='-O2 -Wall -Wextra -DSANTAFE_DADOS_EXPERIMENTAL -DLUA_USE_APICHECK' > evidencias/dados10-helper-pacotes.log 2>&1
python3 experimentos/dados-v10/testar-iba.py > evidencias/dados10-iba-sdk.log 2>&1
printf '%s\n' 'IBA3_DEBIAN_OK'
python3 experimentos/dados-v10/testar.py
python3 testes/integracao/testar_pacotes.py > evidencias/dados10-pacotes.log 2>&1
python3 experimentos/dados-v5/testar-aplicativos.py > evidencias/dados10-aplicativos.log 2>&1
python3 experimentos/dados-v6/testar-operacao.py "$SANTAFE_ESTAVEL" > evidencias/dados10-operacao.log 2>&1
(
 source /opt/emsdk/emsdk_env.sh
 export EM_CACHE="$(pwd)/../cache-emscripten"
 bash experimentos/dados-v7/construir-wasm.sh
) > evidencias/dados10-wasm.log 2>&1
printf '%s\n' 'DADOS10_DEBIAN_E_WASM_OK'
