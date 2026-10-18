#!/usr/bin/env bash

set -Eeuo pipefail

if [[ -e /etc/santafe-nomes/zonas.fé || ! -e /etc/santafe/dns-zonas.fé ]]; then
    PADRAO_ZONAS="/etc/santafe-nomes/zonas.fé"
    PADRAO_AMBIENTE="/etc/santafe-nomes/nomes.env"
    PADRAO_SERVICO="nomes-autoridade.service"
    PADRAO_APLICATIVO="/opt/santafe-nomes/autoridade.fé"
    PADRAO_USUARIO="nomes-santafe"
    PADRAO_GRUPO="nomes-santafe"
    PADRAO_VARIAVEL_ZONAS="NOMES_ZONAS_ARQUIVO"
    PADRAO_VARIAVEL_ENDERECO="NOMES_AUTORIDADE_ENDERECO"
    PADRAO_VARIAVEL_PORTA="NOMES_AUTORIDADE_PORTA"
else
    # Compatibilidade operacional com o secundário anterior ao batismo
    # público de Nomes. A zona resultante e sua API continuam sendo Nomes.
    PADRAO_ZONAS="/etc/santafe/dns-zonas.fé"
    PADRAO_AMBIENTE="/etc/santafe/dns.env"
    PADRAO_SERVICO="dns-autoritativo.service"
    PADRAO_APLICATIVO="/opt/santafe-dns/autoritativo.fé"
    PADRAO_USUARIO="dns-santafe"
    PADRAO_GRUPO="dns-santafe"
    PADRAO_VARIAVEL_ZONAS="DNS_ZONAS_ARQUIVO"
    PADRAO_VARIAVEL_ENDERECO="DNS_AUTORITATIVO_ENDERECO"
    PADRAO_VARIAVEL_PORTA="DNS_AUTORITATIVO_PORTA"
fi

ARQUIVO_ZONAS="${NOMES_ZONAS_ARQUIVO:-$PADRAO_ZONAS}"
ARQUIVO_AMBIENTE="${NOMES_AMBIENTE_ARQUIVO:-$PADRAO_AMBIENTE}"
SERVICO="${NOMES_SERVICO:-$PADRAO_SERVICO}"
APLICATIVO="${NOMES_APLICATIVO:-$PADRAO_APLICATIVO}"
USUARIO="${NOMES_USUARIO:-$PADRAO_USUARIO}"
GRUPO="${NOMES_GRUPO:-$PADRAO_GRUPO}"
VARIAVEL_ZONAS="${NOMES_VARIAVEL_ZONAS:-$PADRAO_VARIAVEL_ZONAS}"
VARIAVEL_ENDERECO="${NOMES_VARIAVEL_ENDERECO:-$PADRAO_VARIAVEL_ENDERECO}"
VARIAVEL_PORTA="${NOMES_VARIAVEL_PORTA:-$PADRAO_VARIAVEL_PORTA}"
ZONA="252.208.143.in-addr.arpa."
SN1="sn1.telemulti.net.br."
SN2="sn2.telemulti.net.br."
SN1_IP="143.208.252.1"
SN2_IP="143.208.252.3"
RESPONSAVEL="dns.telemulti.net.br."
MODO="${1:---transicao}"
if [[ -n "${NOMES_SERIE:-}" ]]; then
    SERIE="$NOMES_SERIE"
elif [[ "$MODO" == "--finalizar" ]]; then
    SERIE="2026090302"
else
    SERIE="2026090301"
fi
UNIDADE_PREVIA="santafe-preflight-reversa-telemulti.service"

TRABALHO=""
COPIA=""
PUBLICANDO=0

falhe() {
    printf 'ERRO: %s\n' "$*" >&2
    exit 1
}

pare_previa() {
    systemctl stop "$UNIDADE_PREVIA" >/dev/null 2>&1 || true
    systemctl reset-failed "$UNIDADE_PREVIA" >/dev/null 2>&1 || true
}

restaure() {
    local codigo="${1:-1}"
    trap - ERR
    set +e
    pare_previa
    if [[ "$PUBLICANDO" -eq 1 && -n "$COPIA" && -f "$COPIA/zonas.fé" ]]; then
        echo "ERRO: migração interrompida; restaurando a zona anterior."
        install -o root -g "$GRUPO" -m 0640 "$COPIA/zonas.fé" "$ARQUIVO_ZONAS"
        systemctl restart "$SERVICO"
        echo "Zona anterior restaurada. Cópia: $COPIA"
    fi
    [[ -n "$TRABALHO" && -d "$TRABALHO" ]] && rm -rf -- "$TRABALHO"
    exit "$codigo"
}

trap 'restaure $?' ERR INT TERM

[[ "$(id -u)" -eq 0 ]] || falhe "execute como root"
[[ "$MODO" == "--transicao" || "$MODO" == "--finalizar" ]] ||
    falhe "use --transicao ou --finalizar"
[[ -r "$ARQUIVO_ZONAS" ]] || falhe "não foi possível ler $ARQUIVO_ZONAS"
[[ -r "$ARQUIVO_AMBIENTE" ]] || falhe "não foi possível ler $ARQUIVO_AMBIENTE"
[[ -r "$APLICATIVO" ]] || falhe "não foi possível ler $APLICATIVO"
[[ "$SERIE" =~ ^[0-9]{10}$ ]] || falhe "a série precisa ter dez algarismos"
for variavel in "$VARIAVEL_ZONAS" "$VARIAVEL_ENDERECO" "$VARIAVEL_PORTA"; do
    [[ "$variavel" =~ ^[A-Z][A-Z0-9_]*$ ]] ||
        falhe "nome de variável de ambiente inválido: $variavel"
done

for comando in awk cmp dig grep install runuser systemctl systemd-run; do
    command -v "$comando" >/dev/null || falhe "comando ausente: $comando"
done

echo "==> Conferindo os nomes institucionais em dois resolvedores"
for resolvedor in 1.1.1.1 8.8.8.8; do
    dig +short A "${SN1%.}" "@$resolvedor" | grep -Fx "$SN1_IP" >/dev/null ||
        falhe "$SN1 não aponta para $SN1_IP em $resolvedor"
    dig +short A "${SN2%.}" "@$resolvedor" | grep -Fx "$SN2_IP" >/dev/null ||
        falhe "$SN2 não aponta para $SN2_IP em $resolvedor"
done

DIRETORIO_CONFIGURACAO="$(dirname "$ARQUIVO_ZONAS")"
TRABALHO="$(mktemp -d "$DIRETORIO_CONFIGURACAO/.reversa-telemulti.XXXXXX")"
TEMPORARIO="$TRABALHO/zonas.fé"
BLOCO="$TRABALHO/reversa.fé"

awk -v zona="$ZONA" -v sn1="$SN1" -v sn2="$SN2" \
    -v responsavel="$RESPONSAVEL" -v serie="$SERIE" -v modo="$MODO" '
function saldo(texto, copia, abre, fecha) {
    copia = texto
    abre = gsub(/\{/, "", copia)
    copia = texto
    fecha = gsub(/\}/, "", copia)
    return abre - fecha
}
{
    linha = $0
    if (adiandoNS) {
        blocoNS = blocoNS "\n" linha
        profundidade += saldo(linha)
        if (profundidade == 2) {
            if (blocoNS !~ /ns[12]\.xn--santaf-gva\.dev\.br\./) print blocoNS
            adiandoNS = 0
            blocoNS = ""
        }
        next
    }
    if (!dentro && index(linha, "nome = \"" zona "\"") > 0) {
        dentro = 1
        profundidade = 1
        encontradas++
    }
    if (dentro) {
        if (linha ~ /mestre[[:space:]]*=/) {
            sub(/mestre[[:space:]]*=[[:space:]]*"[^"]*"/,
                "mestre = \"" sn1 "\"", linha)
        }
        if (linha ~ /responsável[[:space:]]*=/) {
            sub(/responsável[[:space:]]*=[[:space:]]*"[^"]*"/,
                "responsável = \"" responsavel "\"", linha)
        }
        if (linha ~ /série[[:space:]]*=[[:space:]]*[0-9]+/) {
            sub(/série[[:space:]]*=[[:space:]]*[0-9]+/,
                "série = " serie, linha)
        }
        # Uma segunda execução substitui, em vez de duplicar, os NS novos
        # de uma linha produzidos por este publicador.
        if (profundidade == 2 &&
            linha ~ /tipo[[:space:]]*=[[:space:]]*"NS"/ &&
            (index(linha, sn1) > 0 || index(linha, sn2) > 0)) next

        if (modo == "--finalizar" &&
            profundidade == 2 &&
            linha ~ /tipo[[:space:]]*=[[:space:]]*"NS"/ &&
            linha ~ /ns[12]\.xn--santaf-gva\.dev\.br\./) next

        # Os NS antigos podem ocupar mais de uma linha na configuração
        # legada. Adia a emissão do registro até conhecer seus dados.
        if (modo == "--finalizar" &&
            profundidade == 2 &&
            linha ~ /tipo[[:space:]]*=[[:space:]]*"NS"/ &&
            saldo(linha) > 0) {
            adiandoNS = 1
            blocoNS = linha
            profundidade += saldo(linha)
            next
        }
    }
    print linha
    if (dentro) {
        # Inserir no início evita depender de vírgula no último registro.
        if (linha ~ /registros[[:space:]]*=[[:space:]]*\{/) {
            print "            { nome = \"@\", tipo = \"NS\", dados = \"" sn1 "\" },"
            print "            { nome = \"@\", tipo = \"NS\", dados = \"" sn2 "\" },"
        }
        profundidade += saldo(linha)
        if (profundidade == 0) dentro = 0
    }
}
END {
    if (encontradas != 1) exit 42
}
' "$ARQUIVO_ZONAS" > "$TEMPORARIO" ||
    falhe "a zona reversa não foi encontrada uma única vez"

awk -v zona="$ZONA" '
function saldo(texto, copia, abre, fecha) {
    copia = texto; abre = gsub(/\{/, "", copia)
    copia = texto; fecha = gsub(/\}/, "", copia)
    return abre - fecha
}
{
    if (!dentro && index($0, "nome = \"" zona "\"") > 0) {
        dentro = 1; profundidade = 1
    }
    if (dentro) print
    if (dentro) {
        profundidade += saldo($0)
        if (profundidade == 0) exit
    }
}
' "$TEMPORARIO" > "$BLOCO"

grep -F "mestre = \"$SN1\"" "$BLOCO" >/dev/null
grep -F "responsável = \"$RESPONSAVEL\"" "$BLOCO" >/dev/null
grep -F "série = $SERIE" "$BLOCO" >/dev/null
grep -F "dados = \"$SN1\"" "$BLOCO" >/dev/null
grep -F "dados = \"$SN2\"" "$BLOCO" >/dev/null
if [[ "$MODO" == "--finalizar" ]]; then
    ! grep -Eq 'ns[12]\.xn--santaf-gva\.dev\.br\.' "$BLOCO" ||
        falhe "os servidores antigos ainda aparecem na zona reversa"
fi

chown root:"$GRUPO" "$TEMPORARIO"
chmod 0640 "$TEMPORARIO"
chown root:"$GRUPO" "$TRABALHO"
chmod 0750 "$TRABALHO"

echo "==> Validando a configuração e a assinatura em 127.0.0.1:15353"
pare_previa
systemd-run --unit="$UNIDADE_PREVIA" --uid="$USUARIO" --gid="$GRUPO" \
    --working-directory="$(dirname "$APLICATIVO")" \
    --property="EnvironmentFile=$ARQUIVO_AMBIENTE" \
    /usr/bin/env \
    "$VARIAVEL_ZONAS=$TEMPORARIO" \
    "$VARIAVEL_ENDERECO=127.0.0.1" \
    "$VARIAVEL_PORTA=15353" \
    GSETTINGS_BACKEND=memory \
    /usr/local/bin/santafé "$APLICATIVO"

PRONTO=0
for _ in {1..80}; do
    if dig @127.0.0.1 -p 15353 "$ZONA" SOA +norecurse +short |
       grep -F "$SN1" >/dev/null; then
        PRONTO=1
        break
    fi
    sleep 0.25
done
if [[ "$PRONTO" -ne 1 ]]; then
    systemctl status "$UNIDADE_PREVIA" --no-pager -l >&2 || true
    journalctl -u "$UNIDADE_PREVIA" -n 100 --no-pager -l >&2 || true
    false
fi
dig @127.0.0.1 -p 15353 "$ZONA" NS +dnssec +norecurse |
    grep -F 'RRSIG' >/dev/null
dig @127.0.0.1 -p 15353 -x 143.208.252.1 +dnssec +norecurse |
    grep -F 'RRSIG' >/dev/null
pare_previa

COPIA="/var/backups/santafe-reversa-telemulti-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$COPIA"
cp -a "$ARQUIVO_ZONAS" "$COPIA/zonas.fé"
systemctl cat "$SERVICO" > "$COPIA/unidade.txt"

echo "==> Instalando a autoridade reversa institucional"
PUBLICANDO=1
install -o root -g "$GRUPO" -m 0640 "$TEMPORARIO" "$ARQUIVO_ZONAS"
systemctl restart "$SERVICO"

ENDERECO_LOCAL="$(awk -F= -v chave="$VARIAVEL_ENDERECO" \
    '$1 == chave { gsub(/[[:space:]"]/, "", $2); print $2; exit }' \
    "$ARQUIVO_AMBIENTE")"
[[ -n "$ENDERECO_LOCAL" ]] || falhe "endereço da autoridade não encontrado"

PRONTO=0
for _ in {1..80}; do
    if systemctl is-active --quiet "$SERVICO" &&
       dig +time=1 +tries=1 @"$ENDERECO_LOCAL" "$ZONA" \
           SOA +norecurse +short 2>/dev/null | grep -F "$SN1" >/dev/null; then
        PRONTO=1
        break
    fi
    sleep 0.25
done
if [[ "$PRONTO" -ne 1 ]]; then
    systemctl status "$SERVICO" --no-pager -l >&2 || true
    journalctl -u "$SERVICO" -n 100 --no-pager -l >&2 || true
    falhe "a autoridade instalada não ficou pronta no tempo esperado"
fi

dig @"$ENDERECO_LOCAL" "$ZONA" SOA +dnssec +norecurse |
    grep -F "$SN1" >/dev/null
dig @"$ENDERECO_LOCAL" "$ZONA" NS +dnssec +norecurse |
    grep -F "$SN2" >/dev/null
dig @"$ENDERECO_LOCAL" -x 143.208.252.1 +dnssec +norecurse |
    grep -F 'RRSIG' >/dev/null

PUBLICANDO=0
rm -rf -- "$TRABALHO"
TRABALHO=""
trap - ERR INT TERM

echo "Autoridade reversa Telemulti instalada e validada neste servidor."
echo "Modo: $MODO; série: $SERIE; cópia: $COPIA"
if [[ "$MODO" == "--transicao" ]]; then
    echo "Os NS antigos foram preservados até a delegação pública mudar."
else
    echo "Os NS antigos foram retirados da zona após a transição."
fi
