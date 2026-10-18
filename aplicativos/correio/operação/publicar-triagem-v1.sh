#!/usr/bin/env bash

set -Eeuo pipefail

PACOTE="/tmp/santafe-triagem-v1-20260830.tar.gz"
SOMA="${PACOTE}.sha256"
RAIZ_PACOTE="santafe-triagem-v1-20260830"
AMBIENTE="/etc/santafe/correio.env"
DESTINO_BIBF="/usr/local/share/santafé/1.0/bibf"
DESTINO_CORREIO="/opt/correio"
DESTINO_CARTEIRO="/opt/carteiro"
DESTINO_CSS="/var/www/santafé.dev.br/carteiro/estático/css/carteiro.css"
DESTINO_MANUAL="/var/www/santafé.dev.br/estático/manual/index.html"
FONTE_SERVIDOR="/home/${SUDO_USER:-rafael}/santafe-fonte"

TRABALHO=""
COPIA=""
PUBLICANDO=0
MIGROU=0

ARQUIVOS_DESTINO=(
    "$DESTINO_BIBF/vigia.fé"
    "$DESTINO_BIBF/correio.fé"
    "$DESTINO_BIBF/correio/triagem.fé"
    "$DESTINO_BIBF/correio/mariadb.fé"
    "$DESTINO_BIBF/correio/LEIA-ME.md"
    "$DESTINO_BIBF/carteiro.fé"
    "$DESTINO_CORREIO/LEIA-ME.md"
    "$DESTINO_CORREIO/banco/estrutura.sql"
    "$DESTINO_CORREIO/banco/migracao-7-triagem-pessoal.sql"
    "$DESTINO_CARTEIRO/carteiro.fé"
    "$DESTINO_CARTEIRO/fonte/carteiro/aplicação.fé"
    "$DESTINO_CARTEIRO/fonte/carteiro/configuração.fé"
    "$DESTINO_CARTEIRO/fonte/carteiro/páginas.fé"
    "$DESTINO_CARTEIRO/fonte/carteiro/web.fé"
    "$DESTINO_CARTEIRO/LEIA-ME.md"
    "$DESTINO_CSS"
    "$DESTINO_MANUAL"
)

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
    if [[ -n "$TRABALHO" && -d "$TRABALHO" ]]; then
        rm -rf -- "$TRABALHO"
    fi
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
        echo "ERRO: publicação interrompida; restaurando a versão anterior."
        systemctl stop correio-envios.timer correio-envios.service \
            correio-recebedor.service carteiro.service 2>/dev/null || true
        tar -xzf "$COPIA/antes.tar.gz" -C /
        while IFS= read -r ausente; do
            [[ -n "$ausente" ]] && rm -f -- "$ausente"
        done < "$COPIA/ausentes.txt"
        if [[ "$MIGROU" -eq 1 ]]; then
            consulta_admin <<'SQL' || true
DELETE FROM correio_migracoes
WHERE componente='correio' AND versao=7;
DROP TABLE IF EXISTS correio_historico_triagem;
DROP TABLE IF EXISTS correio_regras_triagem;
ALTER TABLE correio_cartas
    DROP COLUMN IF EXISTS decidida_em,
    DROP COLUMN IF EXISTS regra_triagem,
    DROP COLUMN IF EXISTS decisao_usuario;
SQL
        fi
        systemctl start correio-recebedor.service carteiro.service || true
        systemctl start correio-envios.timer || true
        echo "Versão anterior restaurada. Cópia de segurança: $COPIA"
    fi
    exit "$codigo"
}

trap limpe EXIT
trap 'restaure "$?" "$LINENO" "$BASH_COMMAND"' ERR

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
TRABALHO="$(mktemp -d /tmp/santafe-triagem-v1.XXXXXX)"
tar -xzf "$PACOTE" -C "$TRABALHO"
RAIZ="$TRABALHO/$RAIZ_PACOTE"

arquivos_obrigatorios=(
    bibs/bibf/vigia.fé
    bibs/bibf/correio.fé
    bibs/bibf/correio/triagem.fé
    bibs/bibf/correio/mariadb.fé
    bibs/bibf/correio/LEIA-ME.md
    bibs/bibf/carteiro.fé
    aplicativos/carteiro/carteiro.fé
    aplicativos/carteiro/fonte/carteiro/aplicação.fé
    aplicativos/carteiro/fonte/carteiro/configuração.fé
    aplicativos/carteiro/fonte/carteiro/páginas.fé
    aplicativos/carteiro/fonte/carteiro/web.fé
    aplicativos/carteiro/estático/css/carteiro.css
    aplicativos/carteiro/LEIA-ME.md
    aplicativos/correio/LEIA-ME.md
    aplicativos/correio/banco/estrutura.sql
    aplicativos/correio/banco/migracao-7-triagem-pessoal.sql
    docs/ARQUITETURA-DO-ECOSSISTEMA.md
    testes/bibf/teste_correio_triagem.fé
    testes/bibc/teste_correio_vigia.fé
    testes/bibc/teste_carteiro_repositorio.fé
    testes/bibc/teste_carteiro_http.fé
    site/manual.html
    site/validar-manual.py
)
for relativo in "${arquivos_obrigatorios[@]}"; do
    [[ -f "$RAIZ/$relativo" ]] || {
        echo "Arquivo ausente no pacote: $relativo" >&2; exit 1;
    }
done

echo "==> Validando fontes, Triagem, Carteiro, Vigia e manual"
for relativo in \
    bibs/bibf/vigia.fé \
    bibs/bibf/correio.fé \
    bibs/bibf/correio/triagem.fé \
    bibs/bibf/correio/mariadb.fé \
    bibs/bibf/carteiro.fé \
    aplicativos/carteiro/carteiro.fé \
    aplicativos/carteiro/fonte/carteiro/aplicação.fé \
    aplicativos/carteiro/fonte/carteiro/configuração.fé \
    aplicativos/carteiro/fonte/carteiro/páginas.fé \
    aplicativos/carteiro/fonte/carteiro/web.fé; do
    /usr/local/bin/santafec -p "$RAIZ/$relativo"
done

(
    cd "$RAIZ"
    export LUA_PATH="$RAIZ/aplicativos/carteiro/fonte/?.fé;$RAIZ/bibs/bibf/?.fé;$DESTINO_BIBF/?.fé;$DESTINO_BIBF/?/ini.fé;;"
    export LUA_CPATH="/usr/local/lib/santafé/1.0/bibc/?.so;;"
    /usr/local/bin/santafé testes/bibf/teste_correio_triagem.fé
    /usr/local/bin/santafé testes/bibc/teste_correio_vigia.fé
    /usr/local/bin/santafé testes/bibc/teste_carteiro_repositorio.fé
    /usr/local/bin/santafé testes/bibc/teste_carteiro_http.fé
)
python3 "$RAIZ/site/validar-manual.py" "$RAIZ/site/manual.html" \
    --compilador /usr/local/bin/santafec

registro="$(consulta_admin -e "SELECT COUNT(*) FROM correio_migracoes WHERE componente='correio' AND versao=7")"
tabelas="$(consulta_admin -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name IN ('correio_regras_triagem','correio_historico_triagem')")"
colunas="$(consulta_admin -e "SELECT COUNT(*) FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='correio_cartas' AND column_name IN ('decisao_usuario','regra_triagem','decidida_em')")"
if [[ "$registro" == "0" ]]; then
    [[ "$tabelas" == "0" && "$colunas" == "0" ]] || {
        echo "Estrutura v7 parcial; nada foi alterado." >&2; exit 1;
    }
elif [[ "$registro" == "1" ]]; then
    [[ "$tabelas" == "2" && "$colunas" == "3" ]] || {
        echo "Estrutura v7 registrada, porém incompleta; nada foi alterado." >&2; exit 1;
    }
else
    echo "Registro duplicado da estrutura v7; nada foi alterado." >&2
    exit 1
fi

for servico in correio-recebedor.service carteiro.service correio-envios.timer; do
    systemctl is-active --quiet "$servico" || {
        echo "$servico não estava ativo; nada foi alterado." >&2; exit 1;
    }
done

COPIA="/var/backups/santafe-triagem-v1-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$COPIA"
: > "$COPIA/ausentes.txt"
existentes=()
for alvo in "${ARQUIVOS_DESTINO[@]}"; do
    if [[ -e "$alvo" ]]; then
        existentes+=("$alvo")
    else
        printf '%s\n' "$alvo" >> "$COPIA/ausentes.txt"
    fi
done
tar -czf "$COPIA/antes.tar.gz" "${existentes[@]}"

PUBLICANDO=1
echo "==> Parando somente os consumidores postais"
systemctl stop correio-envios.timer correio-envios.service \
    correio-recebedor.service carteiro.service

if [[ "$registro" == "0" ]]; then
    echo "==> Aplicando a estrutura v7 da Triagem"
    MIGROU=1
    consulta_admin < "$RAIZ/aplicativos/correio/banco/migracao-7-triagem-pessoal.sql"
fi

echo "==> Conferindo as permissões restritas da aplicação"
caixa_preflight="$(consulta_admin -e "SELECT id FROM correio_caixas ORDER BY id LIMIT 1")"
[[ "$caixa_preflight" =~ ^[0-9]+$ ]] || {
    echo "Nenhuma caixa postal disponível para o ensaio transacional." >&2; exit 1;
}
consulta <<SQL
START TRANSACTION;
INSERT INTO correio_regras_triagem (caixa_id,escopo,valor,decisao)
VALUES ($caixa_preflight,'endereco','preflight-triagem@invalid','separar')
ON DUPLICATE KEY UPDATE decisao=VALUES(decisao);
INSERT INTO correio_historico_triagem (caixa_id,carta_id,acao,escopo,valor)
VALUES ($caixa_preflight,NULL,'regra_separar','endereco','preflight-triagem@invalid');
DELETE FROM correio_regras_triagem
WHERE caixa_id=$caixa_preflight AND escopo='endereco'
  AND valor='preflight-triagem@invalid';
ROLLBACK;
SQL

echo "==> Instalando Triagem, Carteiro e documentação"
install -o root -g root -m 0644 "$RAIZ/bibs/bibf/vigia.fé" \
    "$DESTINO_BIBF/vigia.fé"
install -o root -g root -m 0644 "$RAIZ/bibs/bibf/correio.fé" \
    "$DESTINO_BIBF/correio.fé"
install -o root -g root -m 0644 "$RAIZ/bibs/bibf/correio/triagem.fé" \
    "$DESTINO_BIBF/correio/triagem.fé"
install -o root -g root -m 0644 "$RAIZ/bibs/bibf/correio/mariadb.fé" \
    "$DESTINO_BIBF/correio/mariadb.fé"
install -o root -g root -m 0644 "$RAIZ/bibs/bibf/correio/LEIA-ME.md" \
    "$DESTINO_BIBF/correio/LEIA-ME.md"
install -o root -g root -m 0644 "$RAIZ/bibs/bibf/carteiro.fé" \
    "$DESTINO_BIBF/carteiro.fé"

install -o root -g correio -m 0640 "$RAIZ/aplicativos/correio/LEIA-ME.md" \
    "$DESTINO_CORREIO/LEIA-ME.md"
install -o root -g correio -m 0640 \
    "$RAIZ/aplicativos/correio/banco/estrutura.sql" \
    "$DESTINO_CORREIO/banco/estrutura.sql"
install -o root -g correio -m 0640 \
    "$RAIZ/aplicativos/correio/banco/migracao-7-triagem-pessoal.sql" \
    "$DESTINO_CORREIO/banco/migracao-7-triagem-pessoal.sql"

install -o root -g carteiro -m 0640 \
    "$RAIZ/aplicativos/carteiro/carteiro.fé" "$DESTINO_CARTEIRO/carteiro.fé"
for nome in aplicação.fé configuração.fé páginas.fé web.fé; do
    install -o root -g carteiro -m 0640 \
        "$RAIZ/aplicativos/carteiro/fonte/carteiro/$nome" \
        "$DESTINO_CARTEIRO/fonte/carteiro/$nome"
done
install -o root -g carteiro -m 0640 "$RAIZ/aplicativos/carteiro/LEIA-ME.md" \
    "$DESTINO_CARTEIRO/LEIA-ME.md"
install -o root -g www-data -m 0644 \
    "$RAIZ/aplicativos/carteiro/estático/css/carteiro.css" "$DESTINO_CSS"
install -o root -g www-data -m 0644 "$RAIZ/site/manual.html" "$DESTINO_MANUAL"

echo "==> Reiniciando e validando os serviços"
systemctl start correio-recebedor.service carteiro.service
pronto=0
for tentativa in {1..120}; do
    if systemctl is-active --quiet correio-recebedor.service &&
       systemctl is-active --quiet carteiro.service &&
       curl -fsS --max-time 2 -o "$TRABALHO/estado.json" \
           http://127.0.0.1:7100/carteiro/estado 2>/dev/null &&
       grep -Fq '"estado":"pronto"' "$TRABALHO/estado.json"; then
        pronto=1
        break
    fi
    sleep 0.25
done
if [[ "$pronto" -ne 1 ]]; then
    systemctl status correio-recebedor.service carteiro.service \
        --no-pager -l >&2 || true
    journalctl -u correio-recebedor.service -u carteiro.service \
        -n 80 --no-pager -l >&2 || true
    false
fi

timeout 5 bash -c \
    'exec 3<>/dev/tcp/127.0.0.1/25; IFS= read -r linha <&3; [[ "$linha" == 220* ]]'
grep -Fq 'ap.rota("GET", "/carteiro/triagem"' \
    "$DESTINO_CARTEIRO/fonte/carteiro/aplicação.fé"
grep -Fq 'carteiro.triagem.decisãoDoUsuário' \
    "$DESTINO_CARTEIRO/fonte/carteiro/aplicação.fé"
grep -Fq 'id="carteiro-decida-triagem"' "$DESTINO_MANUAL"

[[ "$(consulta_admin -e "SELECT MAX(versao) FROM correio_migracoes WHERE componente='correio'")" == "7" ]]
[[ "$(consulta_admin -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name IN ('correio_regras_triagem','correio_historico_triagem')")" == "2" ]]
[[ "$(consulta_admin -e "SELECT COUNT(*) FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='correio_cartas' AND column_name IN ('decisao_usuario','regra_triagem','decidida_em')")" == "3" ]]

systemctl start correio-envios.timer
systemctl is-active --quiet correio-envios.timer

echo "==> Atualizando a árvore-fonte do servidor"
if [[ -d "$FONTE_SERVIDOR" ]]; then
    DONO="${SUDO_USER:-rafael}"
    GRUPO="$(id -gn "$DONO")"
    for relativo in "${arquivos_obrigatorios[@]}"; do
        [[ "$relativo" == site/* ]] && continue
        origem="$RAIZ/$relativo"
        destino="$FONTE_SERVIDOR/$relativo"
        mkdir -p "$(dirname "$destino")"
        install -o "$DONO" -g "$GRUPO" -m 0644 "$origem" "$destino"
    done
    if [[ -d "$FONTE_SERVIDOR/site-sfdev" ]]; then
        install -o "$DONO" -g "$GRUPO" -m 0644 "$RAIZ/site/manual.html" \
            "$FONTE_SERVIDOR/site-sfdev/manual.html"
    fi
fi

PUBLICANDO=0
echo "Triagem v1 publicada e validada. Cópia de segurança: $COPIA"
echo "Regras pessoais: endereço exato prevalece sobre domínio."
echo "Decisões do usuário preservam a avaliação automática."
