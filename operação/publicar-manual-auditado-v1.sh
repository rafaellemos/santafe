#!/usr/bin/env bash

set -Eeuo pipefail

MODO="${1:-publicar}"
PACOTE="/tmp/santafe-manual-auditado-20261002.tar.gz"
PACOTE_SHA256="5a6883d2b0275fea4d642eff3c8c7101afb63a81c24cc2ec2eb8cf862da0af07"
RAIZ="/home/rafael/santafe-fonte"
PUBLICO="/var/www/santafé.dev.br/estático/manual/index.html"
FONTE_MANUAL="$RAIZ/site-sfdev/manual.html"
FONTE_VALIDADOR="$RAIZ/site-sfdev/validar-manual.py"
FONTE_RELATORIO="$RAIZ/docs/AUDITORIA-MANUAL-2026-10-02.md"
FONTE_README="$RAIZ/README.md"
URL="https://xn--santaf-gva.dev.br/est%C3%A1tico/manual/index.html"

TRABALHO=""
COPIA=""
ALTEROU=0
RELATORIO_EXISTIA=0

limpe_trabalho() {
    if [[ -n "$TRABALHO" && "$TRABALHO" == /tmp/santafe-manual-auditado.* ]]; then
        rm -rf -- "$TRABALHO"
    fi
}

restaure() {
    local codigo="$1" linha="$2"
    trap - ERR
    set +e
    echo "ERRO: publicação do manual interrompida na linha ${linha} (código ${codigo})." >&2
    if [[ "$ALTEROU" -eq 1 && -n "$COPIA" && -f "$COPIA/antes.tar.gz" ]]; then
        tar -xzf "$COPIA/antes.tar.gz" -C /
        if [[ "$RELATORIO_EXISTIA" -eq 0 ]]; then
            rm -f -- "$FONTE_RELATORIO"
        fi
        echo "Versão anterior restaurada. Cópia de segurança: $COPIA" >&2
    fi
    limpe_trabalho
    exit "$codigo"
}

trap 'restaure "$?" "$LINENO"' ERR
trap 'limpe_trabalho' EXIT

if [[ "$MODO" != "publicar" && "$MODO" != "--preflight" ]]; then
    echo "Uso: $0 [--preflight]" >&2
    exit 2
fi
if [[ "$MODO" == "publicar" && "$EUID" -ne 0 ]]; then
    echo "Execute com sudo." >&2
    exit 1
fi

for comando in python3 tar sha256sum install curl cmp grep mktemp; do
    command -v "$comando" >/dev/null 2>&1 || {
        echo "Comando obrigatório ausente: $comando" >&2
        exit 1
    }
done

[[ -f "$PACOTE" ]] || { echo "Pacote ausente: $PACOTE" >&2; exit 1; }
echo "$PACOTE_SHA256  $PACOTE" | sha256sum -c -
[[ -d "$RAIZ/src" && -f "$RAIZ/src/lbaselib.c" ]] || {
    echo "Fonte Santafé não localizado em $RAIZ." >&2
    exit 1
}

COMPILADOR=""
for candidato in "$RAIZ/src/santafec" /usr/local/bin/santafec /usr/bin/santafec; do
    if [[ -x "$candidato" ]]; then
        COMPILADOR="$candidato"
        break
    fi
done
[[ -n "$COMPILADOR" ]] || { echo "Compilador santafec não encontrado." >&2; exit 1; }

TRABALHO="$(mktemp -d /tmp/santafe-manual-auditado.XXXXXX)"
tar -xzf "$PACOTE" -C "$TRABALHO"
for item in \
    site-sfdev/manual.html \
    site-sfdev/validar-manual.py \
    docs/AUDITORIA-MANUAL-2026-10-02.md \
    README.md
do
    [[ -f "$TRABALHO/$item" ]] || { echo "Arquivo ausente no pacote: $item" >&2; exit 1; }
done

echo "==> Validando estrutura, exemplos e API pública antes da troca"
PYTHONPYCACHEPREFIX="$TRABALHO/pycache" python3 -m py_compile \
    "$TRABALHO/site-sfdev/validar-manual.py"
python3 "$TRABALHO/site-sfdev/validar-manual.py" \
    "$TRABALHO/site-sfdev/manual.html" \
    --compilador "$COMPILADOR" \
    --fonte "$RAIZ"
grep -Fq 'segredo.resumaSHA256(dados)' "$TRABALHO/site-sfdev/manual.html"
grep -Fq 'rede.consulteDNSAssíncrono' "$TRABALHO/site-sfdev/manual.html"
grep -Fq 'Contratos C conferidos:' "$TRABALHO/site-sfdev/validar-manual.py"
if grep -Fiq 'Pão do Café' "$TRABALHO/site-sfdev/manual.html"; then
    echo "O manual Santafé contém referência ao projeto Pão do Café." >&2
    exit 1
fi
if grep -Fq 'A instalação atual usa o Mailjet' "$TRABALHO/site-sfdev/manual.html"; then
    echo "O manual ainda fixa o retransmissor de uma instalação." >&2
    exit 1
fi

if [[ "$MODO" == "--preflight" ]]; then
    echo "Pré-validação do manual concluída; nenhuma instalação foi alterada."
    exit 0
fi

[[ -f "$PUBLICO" ]] || { echo "Manual público ausente: $PUBLICO" >&2; exit 1; }
[[ -f "$FONTE_MANUAL" ]] || { echo "Fonte do manual ausente: $FONTE_MANUAL" >&2; exit 1; }
[[ -f "$FONTE_VALIDADOR" ]] || { echo "Validador instalado ausente: $FONTE_VALIDADOR" >&2; exit 1; }
[[ -f "$FONTE_README" ]] || { echo "README da fonte ausente: $FONTE_README" >&2; exit 1; }
if [[ -f "$FONTE_RELATORIO" ]]; then RELATORIO_EXISTIA=1; fi

COPIA="/var/backups/santafe-manual-auditado-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$COPIA"
itens_copia=("$PUBLICO" "$FONTE_MANUAL" "$FONTE_VALIDADOR" "$FONTE_README")
if [[ "$RELATORIO_EXISTIA" -eq 1 ]]; then itens_copia+=("$FONTE_RELATORIO"); fi
tar -czf "$COPIA/antes.tar.gz" "${itens_copia[@]}"

ALTEROU=1
echo "==> Publicando o manual e sincronizando sua fonte"
install -o root -g www-data -m 0644 \
    "$TRABALHO/site-sfdev/manual.html" "$PUBLICO"
install -D -o rafael -g rafael -m 0644 \
    "$TRABALHO/site-sfdev/manual.html" "$FONTE_MANUAL"
install -D -o rafael -g rafael -m 0755 \
    "$TRABALHO/site-sfdev/validar-manual.py" "$FONTE_VALIDADOR"
install -D -o rafael -g rafael -m 0644 \
    "$TRABALHO/docs/AUDITORIA-MANUAL-2026-10-02.md" "$FONTE_RELATORIO"
install -o rafael -g rafael -m 0644 \
    "$TRABALHO/README.md" "$FONTE_README"

echo "==> Revalidando os arquivos instalados e a resposta HTTPS"
python3 "$FONTE_VALIDADOR" "$FONTE_MANUAL" \
    --compilador "$COMPILADOR" --fonte "$RAIZ"
python3 "$FONTE_VALIDADOR" "$PUBLICO" \
    --compilador "$COMPILADOR" --fonte "$RAIZ"
cmp -s "$PUBLICO" "$FONTE_MANUAL"

curl -fsSL --max-time 20 \
    -o "$TRABALHO/manual-publicado.html" \
    "$URL?v=$PACOTE_SHA256"
cmp -s "$PUBLICO" "$TRABALHO/manual-publicado.html"

ALTEROU=0
echo "Manual Santafé auditado, publicado e validado."
echo "API C conferida diretamente no fonte; Pão do Café permanece fora do manual."
echo "Nenhum serviço precisou ser reiniciado."
echo "Cópia de segurança: $COPIA"
