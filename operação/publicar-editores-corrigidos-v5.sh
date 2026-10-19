#!/usr/bin/env bash
# Atualiza somente o portal, VSIX e catálogo/pacotes Sublime. Sem núcleo/SLS.
set -euo pipefail

readonly PACOTE='/tmp/santafe-editores-vscode-1.0.6-sublime-1.0.13.tar.gz'
readonly SOMA_PACOTE='9297a97b2fb97772b618cb72e3da4e379d886f11b424440bbfb049cdce2efaea'
readonly APLICACAO='/opt/sfdev.fé'
readonly FONTE='/home/rafael/santafe-fonte/site-sfdev'
readonly ESTATICO='/var/www/santafé.dev.br/estático'
readonly DOMINIO='https://xn--santaf-gva.dev.br'
readonly URL_ESTATICO="$DOMINIO/est%C3%A1tico"
MODO="${1:-publicar}"
TRABALHO=''
COPIA=''
ALTEROU=0

falha() {
    local codigo="$1" linha="$2" restaura_ok=1
    trap - ERR INT TERM
    set +e
    echo "ERRO: publicação dos editores interrompida na linha $linha (código $codigo)." >&2
    if [[ "$ALTEROU" -eq 1 ]]; then
        while IFS=$'\t' read -r chave origem destino dono modo; do
            if [[ -f "$COPIA/$chave.antes" ]]; then
                cp -a -- "$COPIA/$chave.antes" "$destino" || restaura_ok=0
            elif [[ -f "$COPIA/$chave.ausente" ]]; then
                rm -f -- "$destino" || restaura_ok=0
            else
                restaura_ok=0
            fi
        done < "$TRABALHO/preparado/plano.tsv"
        systemctl restart sfdev.service || restaura_ok=0
        systemctl is-active --quiet sfdev.service || restaura_ok=0
        if [[ "$restaura_ok" -eq 1 ]]; then
            echo "Arquivos anteriores restaurados. Cópia de segurança: $COPIA" >&2
        else
            echo "ATENÇÃO: restauração incompleta; examine a cópia $COPIA e sfdev.service." >&2
        fi
    else
        echo 'Nenhum arquivo publicado foi alterado.' >&2
    fi
    [[ -z "$TRABALHO" ]] || echo "Diagnóstico preservado em: $TRABALHO" >&2
    exit "$codigo"
}
trap 'falha "$?" "$LINENO"' ERR
trap 'falha 130 "$LINENO"' INT
trap 'falha 143 "$LINENO"' TERM

[[ "$MODO" == publicar || "$MODO" == --preflight ]] || {
    echo "Uso: $0 [--preflight]" >&2; exit 2;
}
if [[ "$MODO" == publicar && "$EUID" -ne 0 ]]; then
    echo 'Execute com sudo bash.' >&2; exit 1
fi
for comando in python3 tar sha256sum install curl cmp mktemp systemctl flock santafec; do
    command -v "$comando" >/dev/null || { echo "Comando ausente: $comando" >&2; exit 1; }
done
if [[ "$MODO" == publicar ]]; then
    exec 9>/run/lock/santafe-editores.lock
    flock -n 9 || { echo 'Já existe uma publicação dos editores em execução.' >&2; exit 1; }
fi

echo 'Publicador dos editores — VS Code 1.0.6 e Sublime 1.0.13'
echo '==> Validando o pacote e preparando a página atual'
printf '%s  %s\n' "$SOMA_PACOTE" "$PACOTE" | sha256sum -c -
TRABALHO="$(mktemp -d /tmp/santafe-editores.XXXXXX)"
tar --no-same-owner -xzf "$PACOTE" -C "$TRABALHO"
(cd "$TRABALHO" && sha256sum -c SHA256SUMS)
python3 "$TRABALHO/preparar-editores-portal.py" \
    --payload "$TRABALHO" --aplicacao "$APLICACAO" \
    --fonte "$FONTE" --estatico "$ESTATICO" --saida "$TRABALHO/preparado"
santafec -p "$TRABALHO/preparado/sfdev.fé"
systemctl is-active --quiet sfdev.service

if [[ "$MODO" == --preflight ]]; then
    echo 'Pré-validação concluída: pacotes íntegros, página compilada e plano pronto.'
    echo 'Nenhum arquivo instalado ou serviço foi alterado.'
    echo "Arquivos preparados em: $TRABALHO"
    exit 0
fi

echo '==> Criando cópia de segurança dos arquivos que serão atualizados'
COPIA="$(mktemp -d "/var/backups/santafe-editores-$(date +%Y%m%d-%H%M%S).XXXXXX")"
cp "$TRABALHO/preparado/plano.tsv" "$COPIA/plano.tsv"
while IFS=$'\t' read -r chave origem destino dono modo; do
    if [[ -f "$destino" ]]; then
        cp -a -- "$destino" "$COPIA/$chave.antes"
    else
        touch "$COPIA/$chave.ausente"
    fi
done < "$TRABALHO/preparado/plano.tsv"

# Não sobrescrever alterações concorrentes entre o preparo e a instalação.
python3 - "$TRABALHO/preparado/antes.sha256.json" <<'PY'
import hashlib, json, pathlib, sys
for nome, esperado in json.load(open(sys.argv[1])).items():
    p = pathlib.Path(nome)
    if p.is_symlink():
        raise SystemExit(f'Destino virou link: {nome}')
    atual = hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
    if atual != esperado:
        raise SystemExit(f'Arquivo alterado durante o preparo: {nome}')
PY

echo '==> Instalando somente página, downloads e catálogo dos editores'
ALTEROU=1
while IFS=$'\t' read -r chave origem destino dono modo; do
    temporario="$(mktemp "$(dirname "$destino")/.santafe-editores.XXXXXX")"
    install -m "$modo" -o "${dono%:*}" -g "${dono#*:}" "$origem" "$temporario"
    mv -f -- "$temporario" "$destino"
    cmp -s "$origem" "$destino"
done < "$TRABALHO/preparado/plano.tsv"

echo '==> Reiniciando somente sfdev.service e aguardando o portal'
systemctl restart sfdev.service
respondeu=0
for tentativa in {1..15}; do
    if systemctl is-active --quiet sfdev.service && \
        curl -fsSL --connect-timeout 3 --max-time 8 \
          "$DOMINIO/baixar?editores=$SOMA_PACOTE" -o "$TRABALHO/pagina-publicada.html"; then
        respondeu=1
        break
    fi
    sleep 1
done
[[ "$respondeu" -eq 1 ]]
python3 - "$TRABALHO/pagina-publicada.html" <<'PY'
import pathlib, sys
pagina = pathlib.Path(sys.argv[1]).read_text()
for esperado in ('Extensão oficial 1.0.6', 'Pacote oficial 1.0.13',
                 'santafe-vscode-1.0.6.vsix', 'Santafe.sublime-package?v=1.0.13',
                 '®var', 'Ⓡvar', 'editores-realce'):
    if esperado not in pagina:
        raise SystemExit(f'Página pública sem: {esperado}')
PY

echo '==> Comparando os downloads HTTPS e o catálogo com os arquivos auditados'
for relativo in \
    baixar/santafe-vscode-1.0.6.vsix \
    baixar/Santafe.sublime-package \
    sublime/Santafe-1.0.13.sublime-package \
    sublime/packages.json
do
    curl -fsSL --connect-timeout 5 --max-time 30 \
        "$URL_ESTATICO/$relativo?v=$SOMA_PACOTE" -o "$TRABALHO/conferido"
    cmp -s "$TRABALHO/$relativo" "$TRABALHO/conferido"
done
curl -fsSL --connect-timeout 5 --max-time 30 \
    "$URL_ESTATICO/baixar/SHA256SUMS?v=$SOMA_PACOTE" -o "$TRABALHO/conferido"
cmp -s "$TRABALHO/preparado/SHA256SUMS" "$TRABALHO/conferido"

ALTEROU=0
trap - ERR INT TERM
echo 'VS Code 1.0.6 e Sublime 1.0.13 publicados e validados.'
echo "Cópia de segurança: $COPIA"
echo 'Página: https://santafé.dev.br/baixar'
echo 'Package Control: catálogo atualizado; instalação manual com cache renovado.'
echo 'Somente sfdev.service reiniciado. Núcleo, SLS, Correio e Pão do Café preservados.'
