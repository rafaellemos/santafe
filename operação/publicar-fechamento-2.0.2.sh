#!/usr/bin/env bash
# Executado pelo lançador com SHA-256 fixado, dentro do pacote já conferido.
set -Eeuo pipefail
MODO="${1:-publicar}"
[[ "$MODO" == publicar || "$MODO" == --preflight ]] || exit 2
[[ "$MODO" == --preflight || "$EUID" -eq 0 ]] || { echo 'Execute com sudo bash.' >&2; exit 1; }
RAIZ="$(cd -- "$(dirname -- "$0")/.." && pwd)"
TRABALHO="$(dirname -- "$RAIZ")"
PACOTES="${SANTAFE_PACOTES_FECHAMENTO:?lançador deve informar os pacotes conferidos}"
PREFIXO="$TRABALHO/prefixo instalado"
SNAPSHOT="$TRABALHO/fonte-publica/santafe-2.0.2"
PREPARADO="$TRABALHO/preparado"
COPIA=''
AJUDANTE="$RAIZ/operação/fechamento-2.0.py"
ESTATICO='/var/www/santafé.dev.br/estático'
URL='https://xn--santaf-gva.dev.br'

falha() {
    local codigo="$1" linha="$2" restaurou=1
    trap - ERR INT TERM
    if (( BASH_SUBSHELL > 0 )); then exit "$codigo"; fi
    set +e
    echo "ERRO: fechamento interrompido na linha $linha (código $codigo)." >&2
    if [[ -n "$COPIA" && -f "$COPIA/touched.json" ]]; then
        python3 "$AJUDANTE" rollback --backup "$COPIA" || restaurou=0
        systemctl restart sfdev.service || restaurou=0
        systemctl is-active --quiet sfdev.service || restaurou=0
        [[ "$restaurou" -eq 1 ]] || echo "ATENÇÃO: examine a restauração em $COPIA" >&2
    else
        echo 'Nenhum arquivo operacional foi trocado.' >&2
    fi
    echo "Diagnóstico preservado em $TRABALHO" >&2
    exit "$codigo"
}
trap 'falha "$?" "$LINENO"' ERR
trap 'falha 130 "$LINENO"' INT
trap 'falha 143 "$LINENO"' TERM

if [[ "$MODO" == publicar ]]; then
    exec 9>/run/lock/santafe-fechamento.lock
    flock -n 9 || { echo 'Outra publicação está ativa.' >&2; exit 1; }
fi
cd "$RAIZ"
export GSETTINGS_BACKEND=memory
echo 'Publicador Santafé 2.0.2 revisão 2 — fixtures temporárias isoladas'
echo '==> Conferindo a distribuição e compilando sem alterar a instalação'
python3 testes/integracao/testar_distribuicao.py "$PACOTES/santafe-2.0.2.tar.gz" "$PACOTES/santafe-2.0.2.zip"
mkdir -p "$TRABALHO/fonte-publica"
tar -xzf "$PACOTES/santafe-2.0.2.tar.gz" -C "$TRABALHO/fonte-publica"
make cbin cbibc
bash testar.sh
python3 testes/integracao/testar_instalador.py
python3 extensões/vscode/testes/testar_extensao.py
python3 extensões/sublime/testes/testar_pacote.py
python3 extensões/sublime/testes/testar_recorte.py
bash instalar.sh --sem-dependencias --prefixo "$PREFIXO"
python3 testes/integracao/testar_instalacao.py "$PREFIXO"
echo '==> Conferindo o núcleo novo com as bibliotecas já instaladas (somente importação)'
env LUA_PATH='/usr/local/share/santafé/1.0/bibf/?.fé;/usr/local/share/santafé/1.0/bibf/?/?.fé;;' \
    LUA_CPATH='/usr/local/lib/santafé/1.0/bibc/?.so;;' \
    "$PREFIXO/bin/santafé" -e 'para _, nome em ipares({"arquivo", "rede", "mariadb", "segredo", "tomada", "correio.imap", "nomes", "rpdf", "vigia"}) início garanta(importe(nome)) fim; mostre("BIBLIOTECAS_INSTALADAS_COMPATIVEIS")'

echo '==> Recompilando e testando o WebAssembly da mesma versão'
if ! command -v emcc >/dev/null; then
    [[ -r /opt/emsdk/emsdk_env.sh ]] || { echo 'Emscripten ausente em /opt/emsdk.' >&2; exit 1; }
    source /opt/emsdk/emsdk_env.sh
fi
# A pré-validação não escreve no SDK compartilhado, que pode pertencer a root.
cache_base="${EM_CACHE:-${EMSDK:-/opt/emsdk}/upstream/emscripten/cache}"
mkdir -p "$TRABALHO/emscripten-cache"
cp -R -- "$cache_base/." "$TRABALHO/emscripten-cache/"
export EM_CACHE="$TRABALHO/emscripten-cache"
(cd src && bash emscripten.sh)
node testes/integracao/testar_wasm.js
node extensões/vscode/testes/testar_api_paletas.js
node extensões/vscode/testes/testar_comportamento.js
node extensões/vscode/testes/testar_sls.js

echo '==> Conferindo os editores públicos e preparando a troca reversível'
cmp extensões/vscode/dist/santafe-1.0.6.vsix "$ESTATICO/baixar/santafe-vscode-1.0.6.vsix"
cmp extensões/sublime/dist/Santafe-1.0.13.sublime-package "$ESTATICO/sublime/Santafe-1.0.13.sublime-package"
python3 "$AJUDANTE" prepare --source "$RAIZ" --snapshot "$SNAPSHOT" \
    --prefix "$PREFIXO" --downloads "$PACOTES" --system /usr/local \
    --site /home/rafael/santafe-fonte/site-sfdev --public "$ESTATICO" --out "$PREPARADO"
src/santafec -p "$PREPARADO/sfdev.fé"
python3 docs/validar-manual.py "$PREPARADO/manual.html" --fonte "$RAIZ" --compilador "$RAIZ/src/santafec"
systemctl is-active --quiet sfdev.service

if [[ "$MODO" == --preflight ]]; then
    echo 'FECHAMENTO_2_0_2_PREFLIGHT_OK — nenhuma instalação ou serviço alterado'
    echo "Evidências e compilação: $TRABALHO"
    exit 0
fi

echo '==> Instalando núcleo/SLS, manual, downloads e executor versionado'
COPIA="$(mktemp -d /var/backups/santafe-fechamento-2.0.2-XXXXXXXX)"
# O ajudante cria seu subdiretório privado e só então começa a transação.
COPIA="$COPIA/transacao"
python3 "$AJUDANTE" install --plan "$PREPARADO/plan.json" --backup "$COPIA"
/usr/local/bin/santafé -v
python3 testes/integracao/testar_instalacao.py /usr/local
python3 docs/validar-manual.py "$ESTATICO/manual/index.html" --fonte "$SNAPSHOT" --compilador /usr/local/bin/santafec

echo '==> Reiniciando somente o portal e verificando o conteúdo público'
systemctl restart sfdev.service
for tentativa in $(seq 1 30); do
    if curl -fsS --max-time 5 "$URL/baixar?fechamento=2.0.2" -o "$TRABALHO/pagina.html" &&
       grep -Fq 'Santafé 2.0.2</h5>' "$TRABALHO/pagina.html"; then break; fi
    sleep 1
done
grep -Fq 'Santafé 2.0.2</h5>' "$TRABALHO/pagina.html"
systemctl is-active --quiet sfdev.service
for item in baixar/santafe-2.0.2.tar.gz baixar/santafe-2.0.2.zip baixar/santafe-2.0.2.json \
            wasm/2.0.2/santafe.js wasm/2.0.2/santafe.wasm manual/index.html; do
    curl -fsSL --max-time 60 "$URL/est%C3%A1tico/$item?verificacao=2.0.2" -o "$TRABALHO/publicado"
    cmp "$ESTATICO/$item" "$TRABALHO/publicado"
done
python3 "$AJUDANTE" verify --plan "$PREPARADO/plan.json"
trap - ERR INT TERM
echo 'Santafé 2.0.2 publicado e validado; SLS 0.1.1; editores preservados.'
echo "Cópia reversível: $COPIA"
echo 'Fonte exato: /home/rafael/santafe-fonte/versoes/2.0.2'
echo 'Bancos, aplicações empresariais e bibliotecas dos serviços não foram alterados.'
echo 'Somente sfdev.service reiniciado; demais processos persistentes mantidos.'
