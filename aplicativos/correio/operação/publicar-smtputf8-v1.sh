#!/usr/bin/env bash

set -Eeuo pipefail

PACOTE="/tmp/santafe-smtputf8-20260831.tar.gz"
SOMA_ESPERADA="891670b640addcb3a0a5faceb75bcccaaa046623bf61271a60cb77a83f2c98a0"
DEST_BIBF="/usr/local/share/santafé/1.0/bibf"
DEST_CORREIO="/opt/correio"
DEST_CARTEIRO="/opt/carteiro"
DEST_MANUAL="/var/www/santafé.dev.br/estático/manual/index.html"
ARVORE_SERVIDOR="/home/${SUDO_USER:-rafael}/santafe-fonte"

TRABALHO=""
RAIZ=""
COPIA=""
PUBLICANDO=0

limpe() {
    if [[ -n "$TRABALHO" && -d "$TRABALHO" ]]; then
        rm -rf -- "$TRABALHO"
    fi
}

aguarde_servico() {
    local servico="$1"
    local tentativa
    for ((tentativa=1; tentativa<=160; tentativa++)); do
        if systemctl is-active --quiet "$servico"; then
            return 0
        fi
        if systemctl is-failed --quiet "$servico"; then
            break
        fi
        sleep 0.25
    done
    systemctl status "$servico" --no-pager -l >&2 || true
    journalctl -u "$servico" -n 80 --no-pager -l >&2 || true
    return 1
}

restaure() {
    local codigo="${1:-1}"
    local linha="${2:-desconhecida}"
    local comando="${3:-desconhecido}"
    trap - ERR
    set +e
    printf 'Falha na linha %s (código %s): %s\n' \
        "$linha" "$codigo" "$comando" >&2
    if [[ "$PUBLICANDO" -eq 1 && -f "$COPIA/antes.tar.gz" ]]; then
        echo "ERRO: atualização SMTPUTF8 interrompida; restaurando a versão anterior."
        systemctl stop carteiro.service correio-agencia.service \
            correio-recebedor.service correio-envios.timer \
            correio-envios.service >/dev/null 2>&1 || true
        tar -xzf "$COPIA/antes.tar.gz" -C /
        while IFS= read -r ausente; do
            [[ -n "$ausente" ]] && rm -f -- "$ausente"
        done < "$COPIA/ausentes.txt"
        systemctl start correio-recebedor.service correio-agencia.service \
            carteiro.service correio-envios.timer >/dev/null 2>&1 || true
        echo "Versão anterior restaurada. Cópia de segurança: $COPIA"
    fi
    exit "$codigo"
}

trap limpe EXIT
trap 'restaure "$?" "$LINENO" "$BASH_COMMAND"' ERR

[[ "$EUID" -eq 0 ]] || { echo "Execute com sudo." >&2; exit 1; }
[[ -f "$PACOTE" ]] || { echo "Pacote ausente: $PACOTE" >&2; exit 1; }
SOMA_ATUAL="$(sha256sum "$PACOTE" | awk '{print $1}')"
[[ "$SOMA_ATUAL" == "$SOMA_ESPERADA" ]] || {
    echo "A soma do pacote não confere; nada foi alterado." >&2
    exit 1
}

for servico in correio-recebedor.service correio-agencia.service \
    correio-imap.service carteiro.service correio-envios.timer; do
    systemctl is-active --quiet "$servico" || {
        echo "$servico não está ativo; nada foi alterado." >&2
        exit 1
    }
done

TRABALHO="$(mktemp -d /tmp/santafe-smtputf8-publicacao.XXXXXX)"
chmod 0755 "$TRABALHO"
RAIZ="$TRABALHO/fonte"
mkdir -p "$RAIZ"
tar -xzf "$PACOTE" -C "$RAIZ"

OBRIGATORIOS=(
    bibs/bibf/correio.fé
    aplicativos/carteiro/fonte/carteiro/aplicação.fé
    aplicativos/correio/LEIA-ME.md
    testes/bibf/teste_correio_mime.fé
    testes/bibf/teste_correio_seguranca.fé
    testes/bibf/teste_correio_agência.fé
    testes/bibf/teste_correio_tls_implicito.fé
    testes/bibc/teste_carteiro_http.fé
    testes/bibc/teste_correio_submissão_smtp.fé
    testes/integração/validar_smtputf8_exato.py
    manual.html
    validar-manual.py
)
for relativo in "${OBRIGATORIOS[@]}"; do
    [[ -f "$RAIZ/$relativo" ]] || {
        echo "Arquivo ausente no pacote: $relativo" >&2
        exit 1
    }
done

echo "==> Validando fontes, SMTPUTF8, Carteiro e manual antes da troca"
for relativo in \
    bibs/bibf/correio.fé \
    aplicativos/carteiro/fonte/carteiro/aplicação.fé \
    testes/bibf/teste_correio_seguranca.fé \
    testes/bibf/teste_correio_tls_implicito.fé; do
    /usr/local/bin/santafec -p "$RAIZ/$relativo"
done
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
    "$RAIZ/testes/integração/validar_smtputf8_exato.py"
(
    cd "$RAIZ"
    export LUA_PATH="$RAIZ/aplicativos/carteiro/fonte/?.fé;$RAIZ/aplicativos/carteiro/fonte/?/ini.fé;$RAIZ/bibs/bibf/?.fé;$RAIZ/bibs/bibf/?/?.fé;$DEST_BIBF/?.fé;$DEST_BIBF/?/?.fé;;"
    export LUA_CPATH="/usr/local/lib/santafé/1.0/bibc/?.so;;"
    timeout 30 /usr/local/bin/santafé testes/bibf/teste_correio_mime.fé
    timeout 30 /usr/local/bin/santafé testes/bibf/teste_correio_seguranca.fé
    timeout 30 /usr/local/bin/santafé testes/bibf/teste_correio_agência.fé
    timeout 30 /usr/local/bin/santafé testes/bibf/teste_correio_tls_implicito.fé
    timeout 30 /usr/local/bin/santafé testes/bibc/teste_carteiro_http.fé
    timeout 30 /usr/local/bin/santafé testes/bibc/teste_correio_submissão_smtp.fé
)
python3 "$RAIZ/validar-manual.py" "$RAIZ/manual.html" \
    --compilador /usr/local/bin/santafec

COPIA="/var/backups/santafe-smtputf8-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$COPIA"
: > "$COPIA/ausentes.txt"
ALVOS=(
    "$DEST_BIBF/correio.fé"
    "$DEST_CARTEIRO/fonte/carteiro/aplicação.fé"
    "$DEST_CORREIO/LEIA-ME.md"
    "$DEST_MANUAL"
)
if [[ -d "$ARVORE_SERVIDOR" ]]; then
    ALVOS+=(
        "$ARVORE_SERVIDOR/bibs/bibf/correio.fé"
        "$ARVORE_SERVIDOR/aplicativos/carteiro/fonte/carteiro/aplicação.fé"
        "$ARVORE_SERVIDOR/aplicativos/correio/LEIA-ME.md"
        "$ARVORE_SERVIDOR/testes/bibf/teste_correio_seguranca.fé"
        "$ARVORE_SERVIDOR/testes/bibf/teste_correio_tls_implicito.fé"
        "$ARVORE_SERVIDOR/testes/integração/validar_smtputf8_exato.py"
        "$ARVORE_SERVIDOR/site-sfdev/manual.html"
        "$ARVORE_SERVIDOR/site-sfdev/validar-manual.py"
    )
fi
EXISTENTES=()
for alvo in "${ALVOS[@]}"; do
    if [[ -e "$alvo" ]]; then
        EXISTENTES+=("$alvo")
    else
        printf '%s\n' "$alvo" >> "$COPIA/ausentes.txt"
    fi
done
tar -czf "$COPIA/antes.tar.gz" "${EXISTENTES[@]}"

PUBLICANDO=1
echo "==> Parando somente os consumidores do contrato SMTP modificado"
systemctl stop correio-envios.timer
systemctl stop correio-envios.service >/dev/null 2>&1 || true
systemctl stop carteiro.service correio-agencia.service \
    correio-recebedor.service

echo "==> Instalando Correio, Carteiro e documentação"
install -o root -g root -m 0644 "$RAIZ/bibs/bibf/correio.fé" \
    "$DEST_BIBF/correio.fé"
install -o root -g carteiro -m 0640 \
    "$RAIZ/aplicativos/carteiro/fonte/carteiro/aplicação.fé" \
    "$DEST_CARTEIRO/fonte/carteiro/aplicação.fé"
install -o root -g correio -m 0640 "$RAIZ/aplicativos/correio/LEIA-ME.md" \
    "$DEST_CORREIO/LEIA-ME.md"
install -o root -g www-data -m 0644 "$RAIZ/manual.html" "$DEST_MANUAL"

echo "==> Reiniciando e validando os serviços"
systemctl start correio-recebedor.service correio-agencia.service \
    carteiro.service correio-envios.timer
aguarde_servico correio-recebedor.service
aguarde_servico correio-agencia.service
aguarde_servico carteiro.service
aguarde_servico correio-envios.timer
systemctl is-active --quiet correio-imap.service

PRONTO=0
for tentativa in {1..120}; do
    if curl -fsS --max-time 2 -o "$TRABALHO/carteiro.json" \
        http://127.0.0.1:7100/carteiro/estado 2>/dev/null &&
       grep -Fq '"estado":"pronto"' "$TRABALHO/carteiro.json"; then
        PRONTO=1
        break
    fi
    sleep 0.25
done
[[ "$PRONTO" -eq 1 ]]

python3 "$RAIZ/testes/integração/validar_smtputf8_exato.py" \
    --endereco 127.0.0.1 --porta 25 \
    --destinatario 'josé@xn--santaf-gva.dev.br'
runuser -u correio -- env \
    LUA_PATH="$DEST_BIBF/?.fé;$DEST_BIBF/?/?.fé;;" \
    LUA_CPATH="/usr/local/lib/santafé/1.0/bibc/?.so;;" \
    /usr/local/bin/santafé "$RAIZ/testes/bibf/teste_correio_seguranca.fé"
grep -Fq 'nomeDoRemetente' "$DEST_MANUAL"
grep -Fq 'josé@xn--santaf-gva.dev.br' "$DEST_MANUAL"

echo "==> Atualizando a árvore-fonte do servidor"
if [[ -d "$ARVORE_SERVIDOR" ]]; then
    DONO="${SUDO_USER:-rafael}"
    GRUPO="$(id -gn "$DONO")"
    FONTES=(
        bibs/bibf/correio.fé
        aplicativos/carteiro/fonte/carteiro/aplicação.fé
        aplicativos/correio/LEIA-ME.md
        testes/bibf/teste_correio_seguranca.fé
        testes/bibf/teste_correio_tls_implicito.fé
        testes/integração/validar_smtputf8_exato.py
    )
    for relativo in "${FONTES[@]}"; do
        destino="$ARVORE_SERVIDOR/$relativo"
        mkdir -p "$(dirname "$destino")"
        modo=0644
        [[ "$relativo" == *.py ]] && modo=0755
        install -o "$DONO" -g "$GRUPO" -m "$modo" \
            "$RAIZ/$relativo" "$destino"
    done
    if [[ -d "$ARVORE_SERVIDOR/site-sfdev" ]]; then
        install -o "$DONO" -g "$GRUPO" -m 0644 "$RAIZ/manual.html" \
            "$ARVORE_SERVIDOR/site-sfdev/manual.html"
        install -o "$DONO" -g "$GRUPO" -m 0644 "$RAIZ/validar-manual.py" \
            "$ARVORE_SERVIDOR/site-sfdev/validar-manual.py"
    fi
fi

PUBLICANDO=0
echo "SMTPUTF8 interoperável publicado e validado. Cópia: $COPIA"
echo "Parte local Unicode preservada; domínio de cabeçalho em Punycode; nome humano em MIME."
