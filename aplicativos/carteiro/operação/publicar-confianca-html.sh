#!/usr/bin/env bash

set -Eeuo pipefail

PACOTE="/tmp/santafe-carteiro-confianca-20260830-v6.tar.gz"
SOMA="${PACOTE}.sha256"
RAIZ_PACOTE="santafe-carteiro-confianca-20260830-v6"
AMBIENTE="/etc/santafe/correio.env"
TEMPORARIO=""
COPIA=""
ALTEROU=0
ESTRUTURA_NOVA=0
TINHA_ARQUIVO_MIGRACAO=0
FONTE_SERVIDOR="/home/${SUDO_USER:-rafael}/santafe-fonte"

DESTINO_BIBF="/usr/local/share/santafé/1.0/bibf"
DESTINO_CARTEIRO="/opt/carteiro"
DESTINO_CORREIO="/opt/correio"
DESTINO_CSS="/var/www/santafé.dev.br/carteiro/estático/css/carteiro.css"

consulta() {
    MYSQL_PWD="${SANTAFE_MARIADB_SENHA:-}" mariadb \
        --batch --raw --skip-column-names \
        --host="${SANTAFE_MARIADB_HOST:-127.0.0.1}" \
        --port="${SANTAFE_MARIADB_PORTA:-3306}" \
        --user="$SANTAFE_MARIADB_USUARIO" \
        "$SANTAFE_MARIADB_BANCO" "$@"
}

consulta_admin() {
    mariadb --protocol=socket --batch --raw --skip-column-names \
        "$SANTAFE_MARIADB_BANCO" "$@"
}

limpe() {
    if [[ -n "$TEMPORARIO" && -d "$TEMPORARIO" ]]; then
        rm -rf -- "$TEMPORARIO"
    fi
}

restaure() {
    local codigo="${1:-1}"
    local linha="${2:-desconhecida}"
    local comando="${3:-desconhecido}"
    local reiniciou=0
    trap - ERR
    set +e
    echo "Falha na linha $linha (código $codigo): $comando" >&2
    if [[ "$ALTEROU" -eq 1 && -n "$COPIA" && -f "$COPIA/antes.tar.gz" ]]; then
        echo "ERRO: atualização interrompida; restaurando o Carteiro anterior."
        systemctl stop carteiro.service
        tar -xzf "$COPIA/antes.tar.gz" -C /
        if [[ "$TINHA_ARQUIVO_MIGRACAO" -eq 1 ]]; then
            install -o root -g correio -m 0640 "$COPIA/migracao-anterior.sql" \
                "$DESTINO_CORREIO/banco/migracao-carteiro-1-remetentes-confiaveis.sql"
        else
            rm -f "$DESTINO_CORREIO/banco/migracao-carteiro-1-remetentes-confiaveis.sql"
        fi
        systemctl start carteiro.service || reiniciou=1
    fi
    if [[ "$ESTRUTURA_NOVA" -eq 1 ]]; then
        consulta_admin -e "DELETE FROM correio_migracoes WHERE componente='carteiro' AND versao=1; DROP TABLE IF EXISTS correio_remetentes_confiaveis;" \
            || true
    fi
    if [[ "$ALTEROU" -eq 1 ]]; then
        if [[ "$reiniciou" -eq 0 ]]; then
            echo "Versão anterior restaurada. Cópia de segurança: $COPIA"
        else
            echo "ATENÇÃO: arquivos restaurados, mas o Carteiro não reiniciou." >&2
        fi
    fi
    exit "$codigo"
}

trap limpe EXIT
trap 'restaure "$?" "$LINENO" "$BASH_COMMAND"' ERR

exija_igual() {
    local nome="$1"
    local recebido="$2"
    local esperado="$3"
    if [[ "$recebido" != "$esperado" ]]; then
        echo "$nome: esperado '$esperado', recebido '$recebido'." >&2
        return 1
    fi
}

exija_texto() {
    local nome="$1"
    local texto="$2"
    local arquivo="$3"
    if ! grep -Fq -- "$texto" "$arquivo"; then
        echo "$nome: texto obrigatório ausente em $arquivo: $texto" >&2
        return 1
    fi
}

[[ "${EUID}" -eq 0 ]] || { echo "Execute com sudo." >&2; exit 1; }
[[ -f "$PACOTE" && -f "$SOMA" ]] || {
    echo "Pacote ou soma ausente em /tmp." >&2; exit 1;
}
[[ -r "$AMBIENTE" ]] || { echo "Ambiente postal indisponível." >&2; exit 1; }

set -a
# shellcheck disable=SC1090
source "$AMBIENTE"
set +a
: "${SANTAFE_MARIADB_USUARIO:?usuário MariaDB ausente}"
: "${SANTAFE_MARIADB_BANCO:?banco MariaDB ausente}"
[[ "$SANTAFE_MARIADB_BANCO" =~ ^[A-Za-z0-9_]+$ ]] || {
    echo "Nome do banco MariaDB inválido." >&2; exit 1;
}
consulta_admin -e "SELECT 1" >/dev/null

(cd /tmp && sha256sum -c "$(basename "$SOMA")")
TEMPORARIO="$(mktemp -d /tmp/santafe-carteiro-confianca.XXXXXX)"
tar -xzf "$PACOTE" -C "$TEMPORARIO"
RAIZ="$TEMPORARIO/$RAIZ_PACOTE"

for arquivo in \
    "$RAIZ/bibs/bibf/carteiro.fé" \
    "$RAIZ/bibs/bibf/correio/mariadb.fé" \
    "$RAIZ/aplicativos/carteiro/carteiro.fé" \
    "$RAIZ/aplicativos/carteiro/fonte/carteiro/aplicação.fé" \
    "$RAIZ/aplicativos/carteiro/fonte/carteiro/páginas.fé" \
    "$RAIZ/aplicativos/carteiro/fonte/carteiro/web.fé" \
    "$RAIZ/aplicativos/carteiro/estático/css/carteiro.css" \
    "$RAIZ/aplicativos/correio/banco/estrutura.sql" \
    "$RAIZ/aplicativos/correio/banco/migracao-carteiro-1-remetentes-confiaveis.sql" \
    "$RAIZ/testes/bibc/teste_carteiro_http.fé" \
    "$RAIZ/testes/bibc/teste_carteiro_repositorio.fé"; do
    [[ -f "$arquivo" ]] || { echo "Arquivo ausente: $arquivo" >&2; exit 1; }
done

echo "==> Validando fontes e comportamento antes da troca"
while IFS= read -r arquivo; do
    /usr/local/bin/santafec -p "$arquivo"
done <<ARQUIVOS
$RAIZ/bibs/bibf/carteiro.fé
$RAIZ/bibs/bibf/correio/mariadb.fé
$RAIZ/aplicativos/carteiro/carteiro.fé
$RAIZ/aplicativos/carteiro/fonte/carteiro/aplicação.fé
$RAIZ/aplicativos/carteiro/fonte/carteiro/páginas.fé
$RAIZ/aplicativos/carteiro/fonte/carteiro/web.fé
$RAIZ/testes/bibc/teste_carteiro_http.fé
$RAIZ/testes/bibc/teste_carteiro_repositorio.fé
ARQUIVOS

env \
    LUA_PATH="$RAIZ/aplicativos/carteiro/fonte/?.fé;$RAIZ/bibs/bibf/?.fé;$DESTINO_BIBF/?.fé;$DESTINO_BIBF/?/ini.fé;;" \
    LUA_CPATH="/usr/local/lib/santafé/1.0/bibc/?.so;;" \
    /usr/local/bin/santafé "$RAIZ/testes/bibc/teste_carteiro_repositorio.fé"
env \
    LUA_PATH="$RAIZ/aplicativos/carteiro/fonte/?.fé;$RAIZ/bibs/bibf/?.fé;$DESTINO_BIBF/?.fé;$DESTINO_BIBF/?/ini.fé;;" \
    LUA_CPATH="/usr/local/lib/santafé/1.0/bibc/?.so;;" \
    /usr/local/bin/santafé "$RAIZ/testes/bibc/teste_carteiro_http.fé"

registro="$(consulta_admin -e "SELECT COUNT(*) FROM correio_migracoes WHERE componente='carteiro' AND versao=1")"
tabela="$(consulta_admin -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name='correio_remetentes_confiaveis'")"
if [[ "$registro" != "$tabela" ]]; then
    echo "Estrutura de confiança inconsistente; nada foi alterado." >&2
    exit 1
fi
if [[ "$registro" == "1" ]]; then
    :
else
    ESTRUTURA_NOVA=1
    echo "==> Criando as preferências de remetentes confiáveis"
    consulta_admin < "$RAIZ/aplicativos/correio/banco/migracao-carteiro-1-remetentes-confiaveis.sql"
fi

echo "==> Validando as permissões restritas do Carteiro"
consulta <<'SQL'
START TRANSACTION;
INSERT IGNORE INTO correio_remetentes_confiaveis (caixa_id, endereco)
SELECT id, 'preflight-confianca@invalid' FROM correio_caixas ORDER BY id LIMIT 1;
DELETE FROM correio_remetentes_confiaveis
WHERE endereco = 'preflight-confianca@invalid';
ROLLBACK;
SQL

COPIA="/var/backups/santafe-carteiro-confianca-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$COPIA"
tar -czf "$COPIA/antes.tar.gz" \
    "$DESTINO_BIBF/carteiro.fé" \
    "$DESTINO_BIBF/correio/mariadb.fé" \
    "$DESTINO_CARTEIRO/carteiro.fé" \
    "$DESTINO_CARTEIRO/fonte/carteiro/aplicação.fé" \
    "$DESTINO_CARTEIRO/fonte/carteiro/páginas.fé" \
    "$DESTINO_CARTEIRO/fonte/carteiro/web.fé" \
    "$DESTINO_CARTEIRO/LEIA-ME.md" \
    "$DESTINO_CORREIO/LEIA-ME.md" \
    "$DESTINO_CORREIO/banco/estrutura.sql" \
    "$DESTINO_CSS"
if [[ -f "$DESTINO_CORREIO/banco/migracao-carteiro-1-remetentes-confiaveis.sql" ]]; then
    TINHA_ARQUIVO_MIGRACAO=1
    cp -a "$DESTINO_CORREIO/banco/migracao-carteiro-1-remetentes-confiaveis.sql" \
        "$COPIA/migracao-anterior.sql"
fi
ALTEROU=1

echo "==> Instalando a confiança em remetentes e o HTML isolado"
systemctl stop carteiro.service
install -o root -g root -m 0644 "$RAIZ/bibs/bibf/carteiro.fé" \
    "$DESTINO_BIBF/carteiro.fé"
install -o root -g root -m 0644 "$RAIZ/bibs/bibf/correio/mariadb.fé" \
    "$DESTINO_BIBF/correio/mariadb.fé"
install -o root -g carteiro -m 0640 "$RAIZ/aplicativos/carteiro/carteiro.fé" \
    "$DESTINO_CARTEIRO/carteiro.fé"
para_instalar=(aplicação.fé páginas.fé web.fé)
for nome in "${para_instalar[@]}"; do
    install -o root -g carteiro -m 0640 \
        "$RAIZ/aplicativos/carteiro/fonte/carteiro/$nome" \
        "$DESTINO_CARTEIRO/fonte/carteiro/$nome"
done
install -o root -g www-data -m 0644 \
    "$RAIZ/aplicativos/carteiro/estático/css/carteiro.css" "$DESTINO_CSS"
install -o root -g carteiro -m 0640 "$RAIZ/aplicativos/carteiro/LEIA-ME.md" \
    "$DESTINO_CARTEIRO/LEIA-ME.md"
install -o root -g correio -m 0640 "$RAIZ/aplicativos/correio/LEIA-ME.md" \
    "$DESTINO_CORREIO/LEIA-ME.md"
install -o root -g correio -m 0640 \
    "$RAIZ/aplicativos/correio/banco/estrutura.sql" \
    "$DESTINO_CORREIO/banco/estrutura.sql"
install -o root -g correio -m 0640 \
    "$RAIZ/aplicativos/correio/banco/migracao-carteiro-1-remetentes-confiaveis.sql" \
    "$DESTINO_CORREIO/banco/migracao-carteiro-1-remetentes-confiaveis.sql"

systemctl start carteiro.service

echo "==> Validando o Carteiro e a estrutura de confiança"
PRONTO=0
for tentativa in {1..120}; do
    if systemctl is-active --quiet carteiro.service; then
        if curl -fsS --max-time 2 -o "$TEMPORARIO/estado.json" \
            http://127.0.0.1:7100/carteiro/estado 2>/dev/null &&
            grep -Fq '"estado":"pronto"' "$TEMPORARIO/estado.json"; then
            PRONTO=1
            break
        fi
    fi
    sleep 0.25
done
if [[ "$PRONTO" -ne 1 ]]; then
    echo "Carteiro não alcançou o estado pronto em 30 segundos." >&2
    systemctl status carteiro.service --no-pager -l >&2 || true
    journalctl -u carteiro.service -n 60 --no-pager -l >&2 || true
    false
fi
estado="$(<"$TEMPORARIO/estado.json")"
exija_texto "estado HTTP" '"estado":"pronto"' "$TEMPORARIO/estado.json"
registro="$(consulta_admin -e "SELECT COUNT(*) FROM correio_migracoes WHERE componente='carteiro' AND versao=1")"
exija_igual "migração do Carteiro" "$registro" "1"
tabela="$(consulta_admin -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name='correio_remetentes_confiaveis'")"
exija_igual "tabela de confiança" "$tabela" "1"
consulta -e "SELECT COUNT(*) FROM correio_remetentes_confiaveis" >/dev/null
exija_texto "confirmação externa" 'mostrarExterno' \
    "$DESTINO_CARTEIRO/fonte/carteiro/aplicação.fé"
exija_texto "confirmação do HTML" 'mostrarHTML' \
    "$DESTINO_CARTEIRO/fonte/carteiro/aplicação.fé"
exija_texto "controle de confiança" 'Confiar no remetente' \
    "$DESTINO_CARTEIRO/fonte/carteiro/páginas.fé"
exija_texto "bloqueio inicial" 'Mensagem HTML ' \
    "$DESTINO_CARTEIRO/fonte/carteiro/páginas.fé"
exija_texto "CSP das imagens" 'img-src https: data:' \
    "$DESTINO_CARTEIRO/fonte/carteiro/web.fé"
exija_texto "ligações em nova aba" '<base target="_blank">' \
    "$DESTINO_CARTEIRO/fonte/carteiro/web.fé"

echo "==> Atualizando a árvore-fonte após a validação"
if [[ -d "$FONTE_SERVIDOR" ]]; then
    DONO="${SUDO_USER:-rafael}"
    GRUPO="$(id -gn "$DONO")"
    while IFS= read -r relativo; do
        origem="$RAIZ/$relativo"
        destino="$FONTE_SERVIDOR/$relativo"
        mkdir -p "$(dirname "$destino")"
        install -o "$DONO" -g "$GRUPO" -m 0644 "$origem" "$destino"
    done <<'ARQUIVOS'
bibs/bibf/carteiro.fé
bibs/bibf/correio/mariadb.fé
aplicativos/carteiro/carteiro.fé
aplicativos/carteiro/fonte/carteiro/aplicação.fé
aplicativos/carteiro/fonte/carteiro/páginas.fé
aplicativos/carteiro/fonte/carteiro/web.fé
aplicativos/carteiro/estático/css/carteiro.css
aplicativos/carteiro/LEIA-ME.md
aplicativos/correio/LEIA-ME.md
aplicativos/correio/banco/estrutura.sql
aplicativos/correio/banco/migracao-carteiro-1-remetentes-confiaveis.sql
testes/bibc/teste_carteiro_http.fé
testes/bibc/teste_carteiro_repositorio.fé
ARQUIVOS
fi

ALTEROU=0
ESTRUTURA_NOVA=0
trap - ERR
echo "Confiança em remetentes publicada. Cópia de segurança: $COPIA"
echo "Confiar habilita a escolha por carta; nunca carrega conteúdo externo sozinho."
