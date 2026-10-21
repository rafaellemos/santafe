#!/usr/bin/env bash
# Executar pela distribuição com SHA-256 fixado pelo lançador.
# --preflight compila/testa/prepara somente em /tmp; não altera serviços.
set -Eeuo pipefail
mode="${1:-publicar}"
[[ "$mode" == publicar || "$mode" == --preflight ]] || exit 2
[[ "$mode" == --preflight || "$EUID" -eq 0 ]] || { echo 'Execute com sudo bash.' >&2; exit 1; }
source_root="$(cd -- "$(dirname -- "$0")/.." && pwd)"
work="$(dirname -- "$source_root")"
case "$work" in /tmp/santafe-conjunto.*) ;; *) echo 'Use o lançador verificável.' >&2; exit 2;; esac
payload="${SANTAFE_CONJUNTO_PACOTES:?lançador deve informar os arquivos conferidos}"
helper="$source_root/operação/preparar-conjunto.py"
prefix="$work/prefixo instalado"
prepared="$work/preparado"
registry="$work/catalogo"
public='/var/www/santafé.dev.br/estático'
url='https://xn--santaf-gva.dev.br'
backup=''
failure() {
    local code="$1" line="$2" restored=1
    trap - ERR INT TERM
    if (( BASH_SUBSHELL > 0 )); then exit "$code"; fi
    set +e
    echo "ERRO: publicação conjunta interrompida na linha $line (código $code)." >&2
    if [[ -n "$backup" && -f "$backup/touched.json" ]]; then
        python3 "$helper" rollback --backup "$backup" || restored=0
        systemctl restart sfdev.service || restored=0
        systemctl is-active --quiet sfdev.service || restored=0
        [[ "$restored" -eq 1 ]] || echo "ATENÇÃO: confira a restauração em $backup" >&2
    else echo 'Nenhum arquivo operacional foi trocado.' >&2; fi
    echo "Evidências preservadas em $work" >&2
    exit "$code"
}
trap 'failure "$?" "$LINENO"' ERR
trap 'failure 130 "$LINENO"' INT
trap 'failure 143 "$LINENO"' TERM
cd "$source_root"
export GSETTINGS_BACKEND=memory
version="$(python3 -c 'import json; print(json.load(open("operação/conjunto-versoes.json"))["nucleo"])')"
# Impossível publicar com metadados de homologação ou núcleo/SLS antigos.
if [[ "$mode" == --preflight ]]; then python3 operação/verificar-conjunto.py --preflight
else python3 operação/verificar-conjunto.py; fi
if [[ "$mode" == publicar ]]; then
    exec 9>/run/lock/santafe-conjunto.lock
    flock -n 9 || { echo 'Outra publicação conjunta está ativa.' >&2; exit 1; }
fi
echo "==> Validando a distribuição conjunta $version antes de qualquer troca"
python3 testes/integracao/testar_distribuicao.py "$payload/santafe-$version.tar.gz" "$payload/santafe-$version.zip"
mkdir -p "$work/fonte-publica"
tar --no-same-owner -xzf "$payload/santafe-$version.tar.gz" -C "$work/fonte-publica"
snapshot="$work/fonte-publica/santafe-$version"
make cbin cbibc
bash testar.sh
python3 ferramentas/gerar_unicode.py --check
python3 testes/integracao/testar_instalador.py
python3 testes/integracao/testar_sls_aceitacao.py --perfil 1.0 --relatorio "$work/sls-fonte.json"
python3 extensões/vscode/empacotar.py
python3 extensões/sublime/empacotar.py
python3 extensões/vscode/testes/testar_extensao.py
python3 extensões/sublime/testes/testar_pacote.py
python3 extensões/sublime/testes/testar_recorte.py
python3 testes/integracao/testar_publicador_editores.py
python3 testes/integracao/testar_fechamento.py
python3 testes/integracao/testar_publicacao_conjunta.py
make ibin isls ibibc ibibf ipacotes pc INSTALL_TOP="$prefix" SUDO_OU_SU=
python3 testes/integracao/testar_instalacao.py "$prefix"
python3 testes/integracao/testar_pacotes_cli.py --binario "$prefix/bin/santafé"
python3 testes/integracao/testar_sls_aceitacao.py --perfil 1.0 --comando "$prefix/bin/santafé-sls" --relatorio "$work/sls-instalado.json"
echo '==> Conferindo compatibilidade com as bibliotecas operacionais (somente importação)'
env LUA_PATH='/usr/local/share/santafé/1.0/bibf/?.fé;/usr/local/share/santafé/1.0/bibf/?/?.fé;;' \
    LUA_CPATH='/usr/local/lib/santafé/1.0/bibc/?.so;;' \
    "$prefix/bin/santafé" -P -e 'para _,nome em ipares({"arquivo","rede","mariadb","segredo","tomada","correio.imap","nomes","rpdf","vigia"}) início garanta(importe(nome)) fim; mostre("BIBLIOTECAS_OPERACIONAIS_COMPATIVEIS")'
echo '==> Recompilando o WebAssembly sem alterar o SDK compartilhado'
if ! command -v emcc >/dev/null; then
    [[ -r /opt/emsdk/emsdk_env.sh ]] || { echo 'Emscripten ausente.' >&2; exit 1; }
    source /opt/emsdk/emsdk_env.sh
fi
cache_base="${EM_CACHE:-${EMSDK:-/opt/emsdk}/upstream/emscripten/cache}"
mkdir -p "$work/emscripten-cache"
cp -R -- "$cache_base/." "$work/emscripten-cache/"
export EM_CACHE="$work/emscripten-cache"
(cd src && bash emscripten.sh)
node testes/integracao/testar_wasm.js
node extensões/vscode/testes/testar_api_paletas.js
node extensões/vscode/testes/testar_comportamento.js
node extensões/vscode/testes/testar_sls.js
echo '==> Preparando catálogo, portal e transação reversível'
previous=()
if [[ -f "$public/bibliotecas/v1/indice.json" ]]; then previous=(--anterior "$public/bibliotecas/v1"); fi
python3 operação/preparar-catalogo-bibliotecas.py --saida "$registry" "${previous[@]}"
python3 "$helper" prepare --source "$source_root" --snapshot "$snapshot" --prefix "$prefix" \
    --downloads "$payload" --registry "$registry" --system /usr/local \
    --site /home/rafael/santafe-fonte/site-sfdev --public "$public" --app /opt/sfdev.fé --out "$prepared"
src/santafec -p "$prepared/sfdev.fé"
python3 docs/validar-manual.py "$prepared/manual.html" --fonte "$source_root" --compilador "$source_root/src/santafec"
systemctl is-active --quiet sfdev.service
if [[ "$mode" == --preflight ]]; then
    echo "CONJUNTO_PREFLIGHT_OK: $work — nenhuma instalação ou serviço alterado"
    exit 0
fi
echo '==> Instalando núcleo/ferramentas, extensões, manual e catálogo'
backup="$(mktemp -d /var/backups/santafe-conjunto-XXXXXXXX)/transacao"
python3 "$helper" install --plan "$prepared/plan.json" --backup "$backup"
python3 testes/integracao/testar_instalacao.py /usr/local
python3 testes/integracao/testar_pacotes_cli.py --binario /usr/local/bin/santafé
python3 testes/integracao/testar_sls_aceitacao.py --perfil 1.0 --comando /usr/local/bin/santafé-sls --relatorio "$work/sls-publicado.json"
echo '==> Reiniciando somente o portal e conferindo HTTPS'
systemctl restart sfdev.service
for attempt in $(seq 1 30); do
    if curl -fsS --max-time 5 "$url/baixar?conjunto=$version" -o "$work/pagina.html" &&
       grep -Fq "Santafé $version</h5>" "$work/pagina.html"; then break; fi
    sleep 1
done
grep -Fq "Santafé $version</h5>" "$work/pagina.html"
grep -Fq 'bibliotecas-distribuicao' "$work/pagina.html"
# Confere todos os destinos estáticos do plano, inclusive cada pacote .sfp.
python3 - "$prepared/plan.json" "$public" "$work/publicados.json" <<'PY'
import json,sys
from pathlib import Path
from urllib.parse import quote
prefix=Path(sys.argv[2]); rows=[]
for e in json.load(open(sys.argv[1])):
    try: relative=Path(e['target']).relative_to(prefix).as_posix()
    except ValueError: continue
    rows.append({'url':'https://xn--santaf-gva.dev.br/est%C3%A1tico/'+quote(relative), 'sha256':e['sha256']})
Path(sys.argv[3]).write_text(json.dumps(rows))
PY
python3 - "$work/publicados.json" <<'PY'
import hashlib,json,subprocess,sys
for item in json.load(open(sys.argv[1])):
    r=subprocess.run(['curl','--disable','-fsS','--proto','=https','--max-time','60',item['url']],capture_output=True,check=True)
    if hashlib.sha256(r.stdout).hexdigest()!=item['sha256']: raise SystemExit('Conteúdo público divergente: '+item['url'])
print('HTTPS: todos os arquivos publicados conferidos por SHA-256')
PY
python3 "$helper" verify --plan "$prepared/plan.json"
systemctl is-active --quiet sfdev.service
trap - ERR INT TERM
echo "Publicação conjunta $version validada. Cópia reversível: $backup"
echo 'Somente sfdev.service foi reiniciado. Bancos, Correio e Pão do Café não foram alterados.'
echo 'GitHub/Marketplace/canal oficial não são alterados por este publicador.'
