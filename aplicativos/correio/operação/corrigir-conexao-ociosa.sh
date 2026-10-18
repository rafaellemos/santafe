#!/usr/bin/env bash

set -Eeuo pipefail

SO_NOVO=/tmp/mariadb-conexao-ociosa.so
CORREIO_NOVO=/tmp/correio-conexao-ociosa.fé
RECEBEDOR_NOVO=/tmp/recebedor-conexao-ociosa.fé
SO_ATUAL=/usr/local/lib/santafé/1.0/bibc/mariadb.so
CORREIO_ATUAL=/usr/local/share/santafé/1.0/bibf/correio.fé
RECEBEDOR_ATUAL=/opt/correio/recebedor.fé
COPIA=/var/backups/santafe-correio-conexao-ociosa-$(date +%Y%m%d-%H%M%S)
SERVICOS=(sfdev.service carteiro.service correio-recebedor.service)
PUBLICOU=falso

exija_raiz() {
    if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
        echo "ERRO: execute este arquivo com sudo." >&2
        exit 1
    fi
}

confira_artefato() {
    local arquivo=$1 resumo=$2
    [[ -f "$arquivo" ]] || {
        echo "ERRO: artefato ausente: $arquivo" >&2
        exit 1
    }
    printf '%s  %s\n' "$resumo" "$arquivo" | sha256sum -c -
}

instale_atomico() {
    local origem=$1 destino=$2 dono=$3 grupo=$4 modo=$5 temporario
    temporario="${destino}.novo.$$"
    install -o "$dono" -g "$grupo" -m "$modo" "$origem" "$temporario"
    mv -f "$temporario" "$destino"
}

espere_servico() {
    local servico=$1
    for _ in {1..40}; do
        systemctl is-active --quiet "$servico" && return 0
        sleep 0.25
    done
    systemctl status "$servico" --no-pager -l || true
    return 1
}

espere_http() {
    local endereco=$1 destino=$2
    for _ in {1..40}; do
        if curl -fsS --max-time 2 "$endereco" -o "$destino" 2>/dev/null; then
            return 0
        fi
        sleep 0.25
    done
    return 1
}

restaure() {
    local codigo=$?
    set +e
    trap - ERR
    if [[ "$PUBLICOU" == verdadeiro && -d "$COPIA" ]]; then
        echo "ERRO: atualização interrompida; restaurando os arquivos anteriores." >&2
        instale_atomico "$COPIA/mariadb.so" "$SO_ATUAL" root root 0755
        instale_atomico "$COPIA/correio.fé" "$CORREIO_ATUAL" root root 0644
        instale_atomico "$COPIA/recebedor.fé" "$RECEBEDOR_ATUAL" root correio 0640
        systemctl restart "${SERVICOS[@]}"
        echo "Versão anterior restaurada. Cópia: $COPIA" >&2
    fi
    exit "$codigo"
}

exija_raiz
confira_artefato "$SO_NOVO" \
    460f89e9574d3538199ef5b1be219a6b578c5f2c5bd4ae24e7be0d0ab63c9525
confira_artefato "$CORREIO_NOVO" \
    0802860efb947e9b0f9f404d6b851c87c9b7d479d6ab995c8c32058a985c8c15
confira_artefato "$RECEBEDOR_NOVO" \
    30a0848901a0879b927d64fd76ce77373cf09956cf7b926116cf237fad2bcfcc

VALIDACAO=$(mktemp -d /tmp/santafe-validacao-mariadb.XXXXXX)
install -m 0755 "$SO_NOVO" "$VALIDACAO/mariadb.so"
LUA_CPATH="$VALIDACAO/?.so" /usr/local/bin/santafé -e \
    'local m=importe "mariadb"; garanta(tipo(m.criePiscinaAssíncrona)=="função")'
rm -rf -- "$VALIDACAO"

for servico in "${SERVICOS[@]}"; do
    systemctl is-active --quiet "$servico" || {
        echo "ERRO: $servico não estava ativo; nada foi alterado." >&2
        exit 1
    }
done

mkdir -p "$COPIA"
cp -a "$SO_ATUAL" "$COPIA/mariadb.so"
cp -a "$CORREIO_ATUAL" "$COPIA/correio.fé"
cp -a "$RECEBEDOR_ATUAL" "$COPIA/recebedor.fé"
trap restaure ERR

echo "==> Parando os consumidores persistentes da biblioteca MariaDB"
systemctl stop "${SERVICOS[@]}"

echo "==> Instalando a piscina renovável e a resposta SMTP temporária"
PUBLICOU=verdadeiro
instale_atomico "$SO_NOVO" "$SO_ATUAL" root root 0755
instale_atomico "$CORREIO_NOVO" "$CORREIO_ATUAL" root root 0644
instale_atomico "$RECEBEDOR_NOVO" "$RECEBEDOR_ATUAL" root correio 0640

echo "==> Reiniciando e validando os serviços"
systemctl start "${SERVICOS[@]}"
for servico in "${SERVICOS[@]}"; do espere_servico "$servico"; done
espere_http http://127.0.0.1:7000/ /tmp/santafe-validacao-sfdev.html
espere_http http://127.0.0.1:7100/carteiro/estado \
    /tmp/santafe-validacao-carteiro.json
ss -ltn | awk '$4 ~ /:25$/ { encontrou=1 } END { exit !encontrou }'

trap - ERR
echo "Correção publicada. Cópia de segurança: $COPIA"
echo "A piscina renova conexões ociosas; falhas transitórias de RCPT agora retornam SMTP 451."
