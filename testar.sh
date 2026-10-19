#!/usr/bin/env bash

set -euo pipefail

RAIZ="$(cd "$(dirname "$0")" && pwd)"
cd "$RAIZ"

INTERPRETADOR="./src/santafé"
COMPILADOR="./src/santafec"

if [[ ! -x "$INTERPRETADOR" || ! -x "$COMPILADOR" ]]; then
    echo "ERRO: compile o núcleo primeiro com 'make cbin'." >&2
    exit 1
fi

for biblioteca in arquivo rede mariadb segredo tomada; do
    if [[ ! -f "bibs/bibc/$biblioteca/$biblioteca.so" ]]; then
        echo "ERRO: falta bibs/bibc/$biblioteca/$biblioteca.so; rode 'make cbibc'." >&2
        exit 1
    fi
done

export LUA_PATH='bibs/bibf/?.fé;bibs/bibf/?.fe;;'
export LUA_CPATH='bibs/bibc/?/?.so;;'

# Nunca depender de uma chave privada não versionada da máquina de desenvolvimento.
TESTE_DKIM_TEMP=$(mktemp -d)
trap 'rm -f "$TESTE_DKIM_TEMP/chave.pem"; rmdir "$TESTE_DKIM_TEMP"' EXIT
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 \
    -out "$TESTE_DKIM_TEMP/chave.pem" >/dev/null 2>&1
export SANTAFE_TESTE_DKIM_CHAVE="$TESTE_DKIM_TEMP/chave.pem"

echo "==> Conferindo a sintaxe dos fontes Santafé"
while IFS= read -r -d '' arquivo; do
    "$COMPILADOR" -p "$arquivo"
done < <(find exemplos testes bibs/bibf aplicativos -type f \
    \( -name '*.fé' -o -name '*.fé' \) -print0)

echo "==> Executando exemplos"
while IFS= read -r -d '' arquivo; do
    "$INTERPRETADOR" "$arquivo" >/dev/null
done < <(find exemplos -maxdepth 1 -type f \
    \( -name '*.fé' -o -name '*.fé' \) -print0)

testes=(testes/metatabelas.fé)
while IFS= read -r -d '' arquivo; do
    testes+=("$arquivo")
done < <(find testes/bibc testes/bibf -type f -name 'teste_*.f*' -print0)

echo "==> Executando testes"
for arquivo in "${testes[@]}"; do
    printf '    %s\n' "$arquivo"
    case "$arquivo" in
        testes/bibf/teste_correio_configuração_bancos.fé)
            env \
                CORREIO_DEPOSITO='/var/lib/santafé/correio' \
                SANTAFE_MARIADB_BANCO='principal_teste' \
                CORREIO_BANCOS_ADICIONAIS='domínio.example|SECUNDARIO|/var/lib/correio-clientes/secundario/correio' \
                SECUNDARIO_MARIADB_HOST='127.0.0.1' \
                SECUNDARIO_MARIADB_PORTA='3306' \
                SECUNDARIO_MARIADB_USUARIO='teste' \
                SECUNDARIO_MARIADB_SENHA='teste' \
                SECUNDARIO_MARIADB_BANCO='secundario_teste' \
                "$INTERPRETADOR" "$arquivo"
            ;;
        testes/bibf/teste_correio_configuração_multidominio.fé)
            env \
                CORREIO_DKIM_DOMINIO='xn--santaf-gva.dev.br' \
                CORREIO_DKIM_SELETOR='santafe2026' \
                CORREIO_DKIM_CHAVE='/tmp/santafe.pem' \
                CORREIO_DKIM_IDENTIDADES='xn--domnio-5va.example|secundario2026|/tmp/secundario.pem' \
                "$INTERPRETADOR" "$arquivo"
            ;;
        *)
            "$INTERPRETADOR" "$arquivo"
            ;;
    esac
done

echo "==> Validando o isolamento concorrente dos temporários"
python3 ./testes/integracao/testar_temporarios.py

echo "==> Auditando o vocabulário público"
./testes/integracao/testar_vocabulario_publico.sh

echo "==> Validando o Servidor de Linguagem Santafé"
python3 ./testes/integracao/testar_sls.py
python3 ./testes/integracao/testar_sls_robustez.py
python3 ./testes/integracao/testar_unicode.py
python3 ./docs/validar-manual.py

echo "✅ Todos os testes disponíveis passaram."
echo "   Os testes MariaDB são ignorados sem as variáveis SANTAFE_MARIADB_*."
