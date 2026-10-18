#!/usr/bin/env bash

set -Eeuo pipefail

PACOTE="/tmp/santafe-protecao-identidade-local-20260830.tar.gz"
HASH="${PACOTE}.sha256"
RAIZ_FONTE="/home/rafael/santafe-fonte"
MODULO_PRODUCAO="/usr/local/share/santafé/1.0/bibf/correio/autenticação.fé"
RECEBEDOR_PRODUCAO="/opt/correio/recebedor.fé"
MANUAL_PRODUCAO="/var/www/santafé.dev.br/estático/manual/index.html"
SERVICO="correio-recebedor.service"

[[ "${EUID}" -eq 0 ]] || {
    echo "ERRO: execute este publicador com sudo." >&2
    exit 1
}
[[ -f "${PACOTE}" && -f "${HASH}" ]] || {
    echo "ERRO: pacote ou arquivo de hash ausente em /tmp." >&2
    exit 1
}

TEMPORARIO="$(mktemp -d /tmp/santafe-identidade-local.XXXXXX)"
COPIA="/var/backups/santafe-identidade-local-$(date +%Y%m%d-%H%M%S)"
MUDOU=0
FONTE_RECEBEDOR_EXISTIA=0
FONTE_LEIAME_APLICATIVO_EXISTIA=0

limpar() {
    rm -rf -- "${TEMPORARIO}"
}

restaurar() {
    echo "Restaurando a versão anterior..." >&2
    install -o root -g root -m 0644 \
        "${COPIA}/autenticação.fé" "${MODULO_PRODUCAO}"
    install -o correio -g correio -m 0750 \
        "${COPIA}/recebedor.fé" "${RECEBEDOR_PRODUCAO}"
    install -o root -g www-data -m 0644 \
        "${COPIA}/manual.html" "${MANUAL_PRODUCAO}"
    install -o rafael -g rafael -m 0644 \
        "${COPIA}/fonte-autenticação.fé" \
        "${RAIZ_FONTE}/bibs/bibf/correio/autenticação.fé"
    install -o rafael -g rafael -m 0644 \
        "${COPIA}/fonte-correio-LEIA-ME.md" \
        "${RAIZ_FONTE}/bibs/bibf/correio/LEIA-ME.md"
    install -o rafael -g rafael -m 0644 \
        "${COPIA}/fonte-manual.html" \
        "${RAIZ_FONTE}/site-sfdev/manual.html"
    se_fonte_recebedor="${RAIZ_FONTE}/aplicativos/correio/recebedor.fé"
    se_fonte_leiame="${RAIZ_FONTE}/aplicativos/correio/LEIA-ME.md"
    if [[ "${FONTE_RECEBEDOR_EXISTIA}" -eq 1 ]]; then
        install -o rafael -g rafael -m 0755 \
            "${COPIA}/fonte-recebedor.fé" "${se_fonte_recebedor}"
    else
        rm -f -- "${se_fonte_recebedor}"
    fi
    if [[ "${FONTE_LEIAME_APLICATIVO_EXISTIA}" -eq 1 ]]; then
        install -o rafael -g rafael -m 0644 \
            "${COPIA}/fonte-aplicativo-LEIA-ME.md" "${se_fonte_leiame}"
    else
        rm -f -- "${se_fonte_leiame}"
    fi
    systemctl restart "${SERVICO}" || true
}

ao_falhar() {
    codigo=$?
    linha=$1
    trap - ERR
    echo "ERRO: publicação interrompida na linha ${linha} (código ${codigo})." >&2
    systemctl status "${SERVICO}" --no-pager -l || true
    if [[ "${MUDOU}" -eq 1 ]]; then restaurar; fi
    exit "${codigo}"
}

trap limpar EXIT
trap 'ao_falhar ${LINENO}' ERR

echo "==> Conferindo pacote e fontes"
(cd /tmp && sha256sum -c "$(basename "${HASH}")")
tar -xzf "${PACOTE}" -C "${TEMPORARIO}"
CONTEUDO="${TEMPORARIO}/santafe-protecao-identidade-local"

/usr/local/bin/santafec -p "${CONTEUDO}/bibs/bibf/correio/autenticação.fé"
/usr/local/bin/santafec -p "${CONTEUDO}/aplicativos/correio/recebedor.fé"
/usr/local/bin/santafec -p \
    "${CONTEUDO}/testes/integracao/auditar_identidade_santafe_falsa_smtp.fé"
(
    cd "${CONTEUDO}"
    env \
        LUA_PATH="${CONTEUDO}/bibs/bibf/?.fé;${CONTEUDO}/bibs/bibf/?/?.fé;/usr/local/share/santafé/1.0/bibf/?.fé;/usr/local/share/santafé/1.0/bibf/?/?.fé;;" \
        LUA_CPATH="/usr/local/lib/santafé/1.0/bibc/?.so;;" \
        /usr/local/bin/santafé testes/bibf/teste_correio_autenticação.fé
)
python3 "${CONTEUDO}/site/validar-manual.py" \
    "${CONTEUDO}/site/manual.html" \
    --compilador /usr/local/bin/santafec

echo "==> Criando cópia de segurança"
mkdir -p "${COPIA}"
cp -a "${MODULO_PRODUCAO}" "${COPIA}/autenticação.fé"
cp -a "${RECEBEDOR_PRODUCAO}" "${COPIA}/recebedor.fé"
cp -a "${MANUAL_PRODUCAO}" "${COPIA}/manual.html"
cp -a "${RAIZ_FONTE}/bibs/bibf/correio/autenticação.fé" \
    "${COPIA}/fonte-autenticação.fé"
cp -a "${RAIZ_FONTE}/bibs/bibf/correio/LEIA-ME.md" \
    "${COPIA}/fonte-correio-LEIA-ME.md"
cp -a "${RAIZ_FONTE}/site-sfdev/manual.html" \
    "${COPIA}/fonte-manual.html"
if [[ -f "${RAIZ_FONTE}/aplicativos/correio/recebedor.fé" ]]; then
    FONTE_RECEBEDOR_EXISTIA=1
    cp -a "${RAIZ_FONTE}/aplicativos/correio/recebedor.fé" \
        "${COPIA}/fonte-recebedor.fé"
fi
if [[ -f "${RAIZ_FONTE}/aplicativos/correio/LEIA-ME.md" ]]; then
    FONTE_LEIAME_APLICATIVO_EXISTIA=1
    cp -a "${RAIZ_FONTE}/aplicativos/correio/LEIA-ME.md" \
        "${COPIA}/fonte-aplicativo-LEIA-ME.md"
fi

MUDOU=1
echo "==> Instalando a proteção da identidade local"
systemctl stop "${SERVICO}"
install -o root -g root -m 0644 \
    "${CONTEUDO}/bibs/bibf/correio/autenticação.fé" "${MODULO_PRODUCAO}"
install -o correio -g correio -m 0750 \
    "${CONTEUDO}/aplicativos/correio/recebedor.fé" "${RECEBEDOR_PRODUCAO}"
install -o root -g www-data -m 0644 \
    "${CONTEUDO}/site/manual.html" "${MANUAL_PRODUCAO}"

mkdir -p "${RAIZ_FONTE}/aplicativos/correio"
install -o rafael -g rafael -m 0644 \
    "${CONTEUDO}/bibs/bibf/correio/autenticação.fé" \
    "${RAIZ_FONTE}/bibs/bibf/correio/autenticação.fé"
install -o rafael -g rafael -m 0644 \
    "${CONTEUDO}/bibs/bibf/correio/LEIA-ME.md" \
    "${RAIZ_FONTE}/bibs/bibf/correio/LEIA-ME.md"
install -o rafael -g rafael -m 0755 \
    "${CONTEUDO}/aplicativos/correio/recebedor.fé" \
    "${RAIZ_FONTE}/aplicativos/correio/recebedor.fé"
install -o rafael -g rafael -m 0644 \
    "${CONTEUDO}/aplicativos/correio/LEIA-ME.md" \
    "${RAIZ_FONTE}/aplicativos/correio/LEIA-ME.md"
install -o rafael -g rafael -m 0644 \
    "${CONTEUDO}/site/manual.html" \
    "${RAIZ_FONTE}/site-sfdev/manual.html"

echo "==> Reiniciando e comprovando a recusa SMTP 550"
systemctl start "${SERVICO}"
for _ in $(seq 1 40); do
    if systemctl is-active --quiet "${SERVICO}"; then
        ss -H -ltn 'sport = :25' > "${TEMPORARIO}/porta-25.txt"
        if [[ -s "${TEMPORARIO}/porta-25.txt" ]]; then break; fi
    fi
    sleep 0.25
done
systemctl is-active --quiet "${SERVICO}"
ss -H -ltn 'sport = :25' > "${TEMPORARIO}/porta-25.txt"
[[ -s "${TEMPORARIO}/porta-25.txt" ]]

TESTE_CORREIO_PORTA=25 \
TESTE_CORREIO_DESTINATARIO='rafael@santafé.dev.br' \
    /usr/local/bin/santafé \
    "${CONTEUDO}/testes/integracao/auditar_identidade_santafe_falsa_smtp.fé"
python3 "${CONTEUDO}/site/validar-manual.py" "${MANUAL_PRODUCAO}" \
    --compilador /usr/local/bin/santafec

MUDOU=0
echo "Proteção da identidade local publicada e validada."
echo "Cópia de segurança: ${COPIA}"
echo "Domínio próprio sem SPF/DKIM alinhado: SMTP 550 5.7.1."
