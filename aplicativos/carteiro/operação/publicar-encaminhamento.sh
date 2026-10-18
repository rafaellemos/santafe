#!/usr/bin/env bash
set -Eeuo pipefail

PACOTE="${1:-/tmp/santafe-carteiro-encaminhamento-20260829.tar.gz}"
RESUMO_ESPERADO="df4ebf7e84b052eea9ada8b3b5270d25ca8c49d6db6889444629c561b53c11ce"
TEMPORARIO="$(mktemp -d /tmp/santafe-carteiro-encaminhamento.XXXXXX)"
COPIA="/var/backups/santafe-carteiro-encaminhamento-$(date +%Y%m%d-%H%M%S)"
ALTEROU=0

limpe() {
    rm -rf -- "$TEMPORARIO"
}

restaure() {
    local codigo="$?"
    se_nao=0
    trap - ERR
    if [[ "$ALTEROU" == 1 && -f "$COPIA/antes.tar.gz" ]]; then
        echo "ERRO: atualização interrompida; restaurando o Carteiro anterior."
        tar -xzf "$COPIA/antes.tar.gz" -C /
        systemctl restart carteiro.service || se_nao=1
        if [[ "$se_nao" == 0 ]]; then
            echo "Versão anterior restaurada. Cópia: $COPIA"
        else
            echo "ATENÇÃO: os arquivos foram restaurados, mas o serviço não reiniciou." >&2
        fi
    fi
    limpe
    exit "$codigo"
}

trap limpe EXIT
trap restaure ERR

[[ -f "$PACOTE" ]] || { echo "Pacote ausente: $PACOTE" >&2; exit 1; }
echo "$RESUMO_ESPERADO  $PACOTE" | sha256sum -c -
tar -xzf "$PACOTE" -C "$TEMPORARIO"

RAIZ="$TEMPORARIO/carteiro"
for arquivo in \
    "$RAIZ/aplicacao.fe" \
    "$RAIZ/paginas.fe" \
    "$RAIZ/carteiro.css"; do
    [[ -f "$arquivo" ]] || { echo "Arquivo ausente no pacote: $arquivo" >&2; exit 1; }
done

echo "==> Conferindo a sintaxe antes de alterar a produção"
/usr/local/bin/santafec -p "$RAIZ/aplicacao.fe"
/usr/local/bin/santafec -p "$RAIZ/paginas.fe"

mkdir -p "$COPIA"
tar -czf "$COPIA/antes.tar.gz" \
    /opt/carteiro/fonte/carteiro/aplicação.fé \
    /opt/carteiro/fonte/carteiro/páginas.fé \
    /var/www/santafé.dev.br/carteiro/estático/css/carteiro.css
ALTEROU=1

echo "==> Instalando somente os arquivos modificados"
install -o root -g carteiro -m 0640 \
    "$RAIZ/aplicacao.fe" \
    /opt/carteiro/fonte/carteiro/aplicação.fé
install -o root -g carteiro -m 0640 \
    "$RAIZ/paginas.fe" \
    /opt/carteiro/fonte/carteiro/páginas.fé
install -o root -g www-data -m 0644 \
    "$RAIZ/carteiro.css" \
    /var/www/santafé.dev.br/carteiro/estático/css/carteiro.css

systemctl restart carteiro.service

echo "==> Validando o processo, o banco e o caminho público"
for _ in $(seq 1 50); do
    if curl -fsS --max-time 2 \
        http://127.0.0.1:7100/carteiro/estado \
        | grep -q '"estado":"pronto"'; then
        break
    fi
    sleep 0.2
done
systemctl is-active --quiet carteiro.service
curl -fsS --max-time 3 http://127.0.0.1:7100/carteiro/estado \
    | grep -q '"estado":"pronto"'
curl -fsS --max-time 8 \
    https://xn--santaf-gva.dev.br/carteiro/estado \
    | grep -q '"estado":"pronto"'

ALTEROU=0
trap - ERR
echo "Carteiro atualizado e validado. Cópia de segurança: $COPIA"
echo "Encaminhamento disponível com releitura segura dos anexos originais."
