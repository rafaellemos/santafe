#!/usr/bin/env bash
# Executar somente na extração descartável, nunca no fonte/serviço instalado.
set -euo pipefail
task_root=$(pwd -P)
case "$task_root" in
  /tmp/santafe-auditoria-sls.*/santafe-*-auditoria.*) ;;
  *) echo 'ERRO: este ensaio exige a árvore descartável /tmp/santafe-auditoria-sls.*/santafe-*-auditoria.*' >&2; exit 2 ;;
esac
[[ $(id -u) != 0 ]] || { echo 'Não executar como root.' >&2; exit 2; }
unset LUA_PATH LUA_CPATH SANTAFE_SLS
export GSETTINGS_BACKEND=memory
mkdir -p relatorios
make cbin cbibc > relatorios/construcao.log 2>&1
python3 testes/integracao/testar_sls_semantica.py
python3 testes/integracao/testar_sls_cancelamento.py
python3 testes/integracao/testar_sls_memoria.py
python3 testes/integracao/testar_sls_aceitacao.py --perfil 1.0 --relatorio relatorios/sls-linux.json
python3 testes/integracao/medir_sls.py --relatorio relatorios/desempenho-linux.json
bash testar.sh > relatorios/regressao.log 2>&1
task_prefix="$task_root/instalacao com espacos"
make ibin isls ibibc ibibf ipacotes pc INSTALL_TOP="$task_prefix" SUDO_OU_SU= > relatorios/instalacao.log 2>&1
python3 testes/integracao/testar_instalacao.py "$task_prefix"
python3 testes/integracao/testar_pacotes_cli.py --binario "$task_prefix/bin/santafé"
python3 testes/integracao/testar_sls_aceitacao.py --perfil 1.0 --comando "$task_prefix/bin/santafé-sls" --relatorio relatorios/sls-instalado-linux.json
if [[ -r /opt/emsdk/emsdk_env.sh ]]; then
  source /opt/emsdk/emsdk_env.sh >/dev/null
  export EM_CACHE="$task_root/cache-emscripten"
  (cd src && bash emscripten.sh) > relatorios/wasm-build.log 2>&1
  node testes/integracao/testar_wasm.js
else
  echo 'ERRO: WebAssembly não foi validado; Emscripten ausente.' >&2
  exit 1
fi
printf 'AUDITORIA_ISOLADA_SLS_OK\n%s\n' "$task_root/relatorios"
