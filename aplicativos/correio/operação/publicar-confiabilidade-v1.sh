#!/usr/bin/env bash

set -Eeuo pipefail

PACOTE="/tmp/santafe-confiabilidade-v1-20260830.tar.gz"
HASH_ESPERADO="e2bb9c15e7fb297c5f1071403aeff4f8938fa069041b7aa4a5a559f2a7431e27"
AMBIENTE="/etc/santafe/correio.env"
DESTINO_BIBF="/usr/local/share/santafé/1.0/bibf"
DESTINO_CORREIO="/opt/correio"
DESTINO_MANUAL="/var/www/santafé.dev.br/estático/manual/index.html"
FONTE_SERVIDOR="/home/${SUDO_USER:-rafael}/santafe-fonte"

TRABALHO=""
BACKUP=""
PUBLICANDO=0
MIGROU=0

ARQUIVOS_DESTINO=(
    "$DESTINO_BIBF/correio.fé"
    "$DESTINO_BIBF/correio/entrega.fé"
    "$DESTINO_BIBF/correio/mariadb.fé"
    "$DESTINO_BIBF/correio/cd.fé"
    "$DESTINO_BIBF/correio/LEIA-ME.md"
    "$DESTINO_CORREIO/envios.fé"
    "$DESTINO_CORREIO/fonte/correio/configuração.fé"
    "$DESTINO_CORREIO/LEIA-ME.md"
    "$DESTINO_CORREIO/banco/estrutura.sql"
    "$DESTINO_CORREIO/banco/migracao-8-confiabilidade.sql"
    "$DESTINO_CORREIO/banco/reverter-8-confiabilidade.sql"
    "$DESTINO_MANUAL"
)

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
    if [[ "$PUBLICANDO" -eq 1 && -f "$BACKUP/antes.tar.gz" ]]; then
        echo "ERRO: atualização interrompida; restaurando a versão anterior."
        systemctl stop correio-envios.timer correio-envios.service \
            correio-recebedor.service carteiro.service 2>/dev/null || true
        tar -xzf "$BACKUP/antes.tar.gz" -C /
        while IFS= read -r ausente; do
            [[ -n "$ausente" ]] && rm -f -- "$ausente"
        done < "$BACKUP/ausentes.txt"
        if [[ "$MIGROU" -eq 1 ]]; then
            consulta_admin < \
                "$TRABALHO/santafe/aplicativos/correio/banco/reverter-8-confiabilidade.sql" \
                || true
        fi
        systemctl start correio-recebedor.service carteiro.service || true
        systemctl start correio-envios.timer || true
        echo "Versão anterior restaurada. Cópia de segurança: $BACKUP"
    fi
    exit "$codigo"
}

trap limpe EXIT
trap 'restaure "$?" "$LINENO" "$BASH_COMMAND"' ERR

[[ "$EUID" -eq 0 ]] || { echo "Execute com sudo." >&2; exit 1; }
[[ -f "$PACOTE" ]] || { echo "Pacote ausente: $PACOTE" >&2; exit 1; }
[[ -r "$AMBIENTE" ]] || { echo "Ambiente postal indisponível." >&2; exit 1; }

HASH_OBTIDO="$(sha256sum "$PACOTE" | awk '{print $1}')"
[[ "$HASH_OBTIDO" == "$HASH_ESPERADO" ]] || {
    echo "A soma do pacote não confere; nada foi alterado." >&2
    exit 1
}

set -a
# shellcheck disable=SC1090
source "$AMBIENTE"
set +a
: "${SANTAFE_MARIADB_BANCO:?banco MariaDB ausente}"
[[ "$SANTAFE_MARIADB_BANCO" =~ ^[A-Za-z0-9_]+$ ]] || {
    echo "Nome do banco MariaDB inválido." >&2; exit 1;
}
consulta_admin -e "SELECT 1" >/dev/null

TRABALHO="$(mktemp -d /tmp/santafe-confiabilidade-publicacao.XXXXXX)"
tar -xzf "$PACOTE" -C "$TRABALHO"
RAIZ="$TRABALHO/santafe"
MANUAL="$TRABALHO/manual.html"
VALIDADOR="$TRABALHO/validar-manual.py"

ARQUIVOS_PACOTE=(
    bibs/bibf/correio.fé
    bibs/bibf/correio/entrega.fé
    bibs/bibf/correio/mariadb.fé
    bibs/bibf/correio/cd.fé
    bibs/bibf/correio/LEIA-ME.md
    aplicativos/correio/envios.fé
    aplicativos/correio/fonte/correio/configuração.fé
    aplicativos/correio/LEIA-ME.md
    aplicativos/correio/banco/estrutura.sql
    aplicativos/correio/banco/migracao-8-confiabilidade.sql
    aplicativos/correio/banco/reverter-8-confiabilidade.sql
    aplicativos/correio/operação/correio.env.exemplo
    docs/ARQUITETURA-DO-ECOSSISTEMA.md
    docs/PLANEJAMENTO-SEGURANCA-E-TELEMETRIA.md
    testes/bibf/teste_correio_entrega.fé
    testes/bibc/teste_correio_quarentena_mariadb.fé
    testes/bibc/teste_carteiro_repositorio.fé
    testes/bibc/teste_correio_fila_depósito.fé
    testes/integracao/testar_correio_mariadb.sh
)
for relativo in "${ARQUIVOS_PACOTE[@]}"; do
    [[ -f "$RAIZ/$relativo" ]] || {
        echo "Arquivo ausente no pacote: $relativo" >&2; exit 1;
    }
done
[[ -f "$MANUAL" && -f "$VALIDADOR" ]] || {
    echo "Manual ou validador ausente no pacote." >&2; exit 1;
}

echo "==> Validando fontes, política de entrega e manual"
for relativo in \
    bibs/bibf/correio.fé \
    bibs/bibf/correio/entrega.fé \
    bibs/bibf/correio/mariadb.fé \
    bibs/bibf/correio/cd.fé \
    aplicativos/correio/envios.fé \
    aplicativos/correio/fonte/correio/configuração.fé \
    testes/bibf/teste_correio_entrega.fé; do
    /usr/local/bin/santafec -p "$RAIZ/$relativo"
done
(
    cd "$RAIZ"
    LUA_PATH="$RAIZ/bibs/bibf/?.fé;$RAIZ/bibs/bibf/?/?.fé;$DESTINO_BIBF/?.fé;$DESTINO_BIBF/?/ini.fé;;" \
        /usr/local/bin/santafé testes/bibf/teste_correio_entrega.fé
)
python3 "$VALIDADOR" "$MANUAL" --compilador /usr/local/bin/santafec

REGISTRO="$(consulta_admin -e \
    "SELECT COUNT(*) FROM correio_migracoes WHERE componente='correio' AND versao=8")"
TABELA="$(consulta_admin -e \
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name='correio_avisos_entrega'")"
COLUNA="$(consulta_admin -e \
    "SELECT COUNT(*) FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='correio_fila' AND column_name='falhas_internas'")"
if [[ "$REGISTRO" == "0" ]]; then
    [[ "$TABELA" == "0" && "$COLUNA" == "0" ]] || {
        echo "Estrutura v8 parcial; nada foi alterado." >&2; exit 1;
    }
elif [[ "$REGISTRO" == "1" ]]; then
    [[ "$TABELA" == "1" && "$COLUNA" == "1" ]] || {
        echo "Estrutura v8 registrada, porém incompleta; nada foi alterado." >&2
        exit 1
    }
else
    echo "Registro duplicado da estrutura v8; nada foi alterado." >&2
    exit 1
fi

for servico in correio-recebedor.service carteiro.service correio-envios.timer; do
    systemctl is-active --quiet "$servico" || {
        echo "$servico não estava ativo; nada foi alterado." >&2; exit 1;
    }
done
for alvo in \
    "$DESTINO_CORREIO/envios.fé" \
    "$DESTINO_CORREIO/fonte/correio/configuração.fé" \
    "$DESTINO_CORREIO/banco/estrutura.sql"; do
    [[ -f "$alvo" ]] || { echo "Destino ausente: $alvo" >&2; exit 1; }
done

BACKUP="/var/backups/santafe-confiabilidade-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP"
: > "$BACKUP/ausentes.txt"
EXISTENTES=()
for alvo in "${ARQUIVOS_DESTINO[@]}"; do
    if [[ -e "$alvo" ]]; then
        EXISTENTES+=("$alvo")
    else
        printf '%s\n' "$alvo" >> "$BACKUP/ausentes.txt"
    fi
done
tar -czf "$BACKUP/antes.tar.gz" "${EXISTENTES[@]}"
consulta_admin -e "SHOW CREATE TABLE correio_fila" > \
    "$BACKUP/correio_fila-estrutura.txt"

PUBLICANDO=1
echo "==> Parando somente os consumidores postais"
systemctl stop correio-envios.timer correio-envios.service \
    correio-recebedor.service carteiro.service

if [[ "$REGISTRO" == "0" ]]; then
    echo "==> Aplicando a estrutura postal v8"
    consulta_admin < \
        "$RAIZ/aplicativos/correio/banco/migracao-8-confiabilidade.sql"
    MIGROU=1
fi

echo "==> Instalando avisos de entrega, quarentena e documentação"
mkdir -p "$DESTINO_BIBF/correio" "$DESTINO_CORREIO/banco"
install -o root -g root -m 0644 "$RAIZ/bibs/bibf/correio.fé" \
    "$DESTINO_BIBF/correio.fé"
for nome in entrega.fé mariadb.fé cd.fé LEIA-ME.md; do
    install -o root -g root -m 0644 "$RAIZ/bibs/bibf/correio/$nome" \
        "$DESTINO_BIBF/correio/$nome"
done
install -o root -g correio -m 0640 "$RAIZ/aplicativos/correio/envios.fé" \
    "$DESTINO_CORREIO/envios.fé"
install -o root -g correio -m 0640 \
    "$RAIZ/aplicativos/correio/fonte/correio/configuração.fé" \
    "$DESTINO_CORREIO/fonte/correio/configuração.fé"
install -o root -g correio -m 0640 "$RAIZ/aplicativos/correio/LEIA-ME.md" \
    "$DESTINO_CORREIO/LEIA-ME.md"
for nome in estrutura.sql migracao-8-confiabilidade.sql \
        reverter-8-confiabilidade.sql; do
    install -o root -g correio -m 0640 \
        "$RAIZ/aplicativos/correio/banco/$nome" \
        "$DESTINO_CORREIO/banco/$nome"
done
install -o root -g www-data -m 0644 "$MANUAL" "$DESTINO_MANUAL"

echo "==> Reiniciando e validando Correio e Carteiro"
systemctl start correio-recebedor.service carteiro.service
systemctl start correio-envios.timer
PRONTO=0
for tentativa in {1..120}; do
    if systemctl is-active --quiet correio-recebedor.service &&
       systemctl is-active --quiet carteiro.service &&
       systemctl is-active --quiet correio-envios.timer &&
       curl -fsS --max-time 2 -o "$TRABALHO/estado.json" \
           http://127.0.0.1:7100/carteiro/estado 2>/dev/null &&
       grep -Fq '"estado":"pronto"' "$TRABALHO/estado.json"; then
        PRONTO=1
        break
    fi
    sleep 0.25
done
if [[ "$PRONTO" -ne 1 ]]; then
    systemctl status correio-recebedor.service carteiro.service \
        correio-envios.timer --no-pager -l >&2 || true
    journalctl -u correio-recebedor.service -u carteiro.service \
        -n 100 --no-pager -l >&2 || true
    false
fi
timeout 5 bash -c \
    'exec 3<>/dev/tcp/127.0.0.1/25; IFS= read -r linha <&3; [[ "$linha" == 220* ]]'
grep -Fq 'id="correio-entrega-forme-aviso"' "$DESTINO_MANUAL"
grep -Fq 'id="correio-fila-liste-quarentena"' "$DESTINO_MANUAL"

[[ "$(consulta_admin -e \
    "SELECT COUNT(*) FROM correio_migracoes WHERE componente='correio' AND versao=8")" == "1" ]]
[[ "$(consulta_admin -e \
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name='correio_avisos_entrega'")" == "1" ]]
[[ "$(consulta_admin -e \
    "SELECT COUNT(*) FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='correio_fila' AND column_name='falhas_internas'")" == "1" ]]

runuser -u correio -- env \
    LUA_PATH="$DESTINO_BIBF/?.fé;$DESTINO_BIBF/?/?.fé;$DESTINO_BIBF/?/ini.fé;;" \
    /usr/local/bin/santafé -e \
    'local C=importe "correio"; local E=importe "correio.entrega"; garanta(C.versão=="0.4.0"); garanta(E.versão=="1.0.0"); mostre("CONFIABILIDADE_POSTAL_OK")' \
    > "$TRABALHO/modulos.txt"
grep -Fxq 'CONFIABILIDADE_POSTAL_OK' "$TRABALHO/modulos.txt"

echo "==> Atualizando a árvore-fonte do servidor"
if [[ -d "$FONTE_SERVIDOR" ]]; then
    DONO="${SUDO_USER:-rafael}"
    GRUPO="$(id -gn "$DONO")"
    for relativo in "${ARQUIVOS_PACOTE[@]}"; do
        origem="$RAIZ/$relativo"
        destino="$FONTE_SERVIDOR/$relativo"
        mkdir -p "$(dirname "$destino")"
        MODO=0644
        [[ "$relativo" == *.sh ]] && MODO=0755
        install -o "$DONO" -g "$GRUPO" -m "$MODO" "$origem" "$destino"
    done
    if [[ -d "$FONTE_SERVIDOR/site-sfdev" ]]; then
        install -o "$DONO" -g "$GRUPO" -m 0644 "$MANUAL" \
            "$FONTE_SERVIDOR/site-sfdev/manual.html"
        install -o "$DONO" -g "$GRUPO" -m 0644 "$VALIDADOR" \
            "$FONTE_SERVIDOR/site-sfdev/validar-manual.py"
    fi
    install -o "$DONO" -g "$GRUPO" -m 0755 "$0" \
        "$FONTE_SERVIDOR/aplicativos/correio/operação/publicar-confiabilidade-v1.sh"
fi

PUBLICANDO=0
echo "Confiabilidade postal publicada e validada. Cópia de segurança: $BACKUP"
echo "Avisos de atraso/falha, recuo progressivo e quarentena operacional: ativos."
