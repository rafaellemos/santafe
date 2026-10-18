#!/usr/bin/env bash

set -euo pipefail

RAIZ="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$RAIZ"

PREFIXO_MARIADB="${MARIADB_PREFIXO:-}"
if [[ -z "$PREFIXO_MARIADB" ]] && command -v brew >/dev/null 2>&1; then
    PREFIXO_MARIADB="$(brew --prefix mariadb@11.4 2>/dev/null || true)"
fi

localize_binario() {
    local nome="$1" caminho
    caminho="$(command -v "$nome" 2>/dev/null || true)"
    if [[ -n "$caminho" ]]; then
        printf '%s\n' "$caminho"
        return
    fi
    for caminho in "/usr/sbin/$nome" "/usr/bin/$nome"; do
        if [[ -x "$caminho" ]]; then
            printf '%s\n' "$caminho"
            return
        fi
    done
}

if [[ -n "$PREFIXO_MARIADB" ]]; then
    MARIADBD="$PREFIXO_MARIADB/bin/mariadbd"
    MARIADB_INSTALAR="$PREFIXO_MARIADB/bin/mariadb-install-db"
    MARIADB_CLIENTE="$PREFIXO_MARIADB/bin/mariadb"
    MARIADB_ADMIN="$PREFIXO_MARIADB/bin/mariadb-admin"
    MARIADB_DUMP="$PREFIXO_MARIADB/bin/mariadb-dump"
else
    MARIADBD="$(localize_binario mariadbd)"
    MARIADB_INSTALAR="$(localize_binario mariadb-install-db)"
    MARIADB_CLIENTE="$(localize_binario mariadb)"
    MARIADB_ADMIN="$(localize_binario mariadb-admin)"
    MARIADB_DUMP="$(localize_binario mariadb-dump)"
fi

for binario in "$MARIADBD" "$MARIADB_INSTALAR" "$MARIADB_CLIENTE" \
                  "$MARIADB_ADMIN" "$MARIADB_DUMP"; do
    if [[ ! -x "$binario" ]]; then
        echo "ERRO: MariaDB completo não encontrado; instale-o ou defina MARIADB_PREFIXO." >&2
        exit 1
    fi
done

PORTA_BANCO="${TESTE_MARIADB_PORTA:-23306}"
PORTA_RECEBEDOR="${TESTE_CORREIO_PORTA:-2525}"
PORTA_CARTEIRO="${TESTE_CARTEIRO_PORTA:-7100}"
PORTA_DESTINO="${TESTE_DESTINO_PORTA:-2526}"
TEMPORARIO="$(mktemp -d /tmp/santafe-correio-integracao.XXXXXX)"
DADOS="$TEMPORARIO/mariadb"
SOQUETE="$TEMPORARIO/mariadb.sock"
SENHA_TESTE="teste-correio-isolado"
PROCESSOS=()

encerre() {
    local codigo=$?
    local processo
    for processo in "${PROCESSOS[@]:-}"; do
        kill "$processo" 2>/dev/null || true
    done
    for processo in "${PROCESSOS[@]:-}"; do
        wait "$processo" 2>/dev/null || true
    done
    if [[ "$codigo" -ne 0 ]]; then
        local registro
        for registro in "$TEMPORARIO"/mariadb.log \
                        "$TEMPORARIO"/recebedor.log \
                        "$TEMPORARIO"/carteiro.log \
                        "$TEMPORARIO"/destino.log; do
            if [[ -f "$registro" ]]; then
                echo "=== $registro" >&2
                tail -n 100 "$registro" >&2 || true
            fi
        done
    fi
    if [[ "${TESTE_MANTER_TEMPORARIO:-falso}" == "verdadeiro" ]]; then
        echo "Ambiente temporário preservado: $TEMPORARIO" >&2
    else
        rm -rf "$TEMPORARIO"
    fi
    return "$codigo"
}
trap encerre EXIT INT TERM

"$MARIADB_INSTALAR" --no-defaults \
    --datadir="$DADOS" --auth-root-authentication-method=normal \
    --skip-test-db >/dev/null

"$MARIADBD" --no-defaults --datadir="$DADOS" \
    --socket="$SOQUETE" --port="$PORTA_BANCO" --bind-address=127.0.0.1 \
    --pid-file="$TEMPORARIO/mariadb.pid" \
    --log-error="$TEMPORARIO/mariadb.log" --skip-name-resolve \
    --max-connections=64 &
PROCESSOS+=("$!")

CLIENTE_RAIZ=("$MARIADB_CLIENTE" --no-defaults \
    --socket="$SOQUETE" -uroot)
ADMIN=("${CLIENTE_RAIZ[@]}" -N santafe_correio_teste)

pronto=falso
for _ in {1..80}; do
    if "$MARIADB_ADMIN" --no-defaults \
        --socket="$SOQUETE" -uroot ping >/dev/null 2>&1; then
        pronto=verdadeiro
        break
    fi
    sleep 0.1
done
if [[ "$pronto" != verdadeiro ]]; then
    cat "$TEMPORARIO/mariadb.log" >&2
    exit 1
fi

"${CLIENTE_RAIZ[@]}" -e "
CREATE DATABASE santafe_correio_teste CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'santafe_teste'@'127.0.0.1' IDENTIFIED BY '$SENHA_TESTE';
GRANT ALL PRIVILEGES ON santafe_correio_teste.* TO 'santafe_teste'@'127.0.0.1';
FLUSH PRIVILEGES;"
"${CLIENTE_RAIZ[@]}" santafe_correio_teste < \
    testes/recursos/correio-base-mariadb.sql
"${CLIENTE_RAIZ[@]}" santafe_correio_teste < \
    aplicativos/correio/banco/estrutura.sql
# A migração precisa permanecer idempotente: o publicador pode reencontrar
# uma coluna ou um índice criado antes de uma tentativa restaurada.
"${CLIENTE_RAIZ[@]}" santafe_correio_teste < \
    aplicativos/correio/banco/migracao-9-imap.sql
"${CLIENTE_RAIZ[@]}" santafe_correio_teste < \
    aplicativos/correio/banco/reverter-9-imap.sql
"${CLIENTE_RAIZ[@]}" santafe_correio_teste < \
    aplicativos/correio/banco/migracao-9-imap.sql

export LUA_PATH="$RAIZ/bibs/bibf/?.fé;$RAIZ/bibs/bibf/?/?.fé;;"
# Após o ensaio de reversão v9, restaurar também as migrações posteriores.
"${CLIENTE_RAIZ[@]}" santafe_correio_teste < aplicativos/correio/banco/estrutura.sql
export LUA_CPATH="${TESTE_LUA_CPATH:-$RAIZ/bibs/bibc/?/?.so;;}"
SANTAFE_BINARIO="${TESTE_SANTAFE_BINARIO:-./src/santafé}"
export SANTAFE_MARIADB_HOST=127.0.0.1
export SANTAFE_MARIADB_PORTA="$PORTA_BANCO"
export SANTAFE_MARIADB_USUARIO=santafe_teste
export SANTAFE_MARIADB_SENHA="$SENHA_TESTE"
export SANTAFE_MARIADB_BANCO=santafe_correio_teste
export CORREIO_RAIZ="$RAIZ/aplicativos/correio"
export CARTEIRO_RAIZ="$RAIZ/aplicativos/carteiro"
export CORREIO_DEPOSITO="$TEMPORARIO/depósito"
export CORREIO_DOMINIO='santafé.dev.br'
export CORREIO_DOMINIOS_LOCAIS='santafé.dev.br,xn--santaf-gva.dev.br'
export CORREIO_RECEBEDOR_ENDERECO=127.0.0.1
export CORREIO_RECEBEDOR_PORTA="$PORTA_RECEBEDOR"
export CORREIO_RECEBEDOR_NOME=xn--santaf-gva.dev.br
export CORREIO_RECEBEDOR_SEGURANCA=nenhuma
export CORREIO_PISCINA_MINIMA=1
export CORREIO_PISCINA_MAXIMA=4
export CORREIO_PULSO_ARQUIVO="$TEMPORARIO/correio.pulso"
export CORREIO_TRIAGEM_ATIVA=verdadeiro
export CORREIO_AUTENTICACAO_ATIVA=falso
export CARTEIRO_ENDERECO=127.0.0.1
export CARTEIRO_PORTA="$PORTA_CARTEIRO"
export CARTEIRO_PULSO_ARQUIVO="$TEMPORARIO/carteiro.pulso"

echo "==> Consultas preparadas, piscina e fila MariaDB"
SANTAFE_TESTE_SENHA_HASH="$("$SANTAFE_BINARIO" -e 'local S=importe "segredo"; local R=importe "rede"; garanta(S.protejaSenhaAssíncrono("senha-apenas-de-teste", função(valor,falha) garanta(valor,falha); mostre(valor); R.pareLaço() fim)); R.laço()')"
export SANTAFE_TESTE_SENHA_HASH
for teste in testes/bibc/teste_mariadb_preparado.f* \
             testes/bibc/teste_mariadb_piscina.f* \
             testes/bibc/teste_mariadb_piscina_ociosa.f* \
             testes/bibc/teste_correio_mariadb.fé \
             testes/bibc/teste_correio_agência_mariadb.fé \
             testes/bibc/teste_correio_imap_mariadb.fé \
             testes/bibc/teste_correio_imap_append_mariadb.fé \
             testes/bibc/teste_correio_autenticação_mariadb.fé; do
    "$SANTAFE_BINARIO" "$teste"
done

for teste in testes/bibf/teste_correio_spf.fé \
             testes/bibf/teste_correio_dmarc.fé \
             testes/bibf/teste_correio_autenticação.fé; do
    "$SANTAFE_BINARIO" "$teste"
done

BILHETE=bilhete-carteiro-isolado
RESUMO="$("$SANTAFE_BINARIO" -e \
    'local segredo=importe "segredo"; mostre(segredo.resumaBilhete("bilhete-carteiro-isolado"))')"
"${CLIENTE_RAIZ[@]}" santafe_correio_teste -e "
INSERT INTO usuarios (nome,usuario,email,papel,estado) VALUES
('Ana','ana','ana@santafé.dev.br','usuário','ativo'),
('Bia','bia','bia@santafé.dev.br','usuário','ativo');
INSERT INTO sessoes (usuario_id,token_hash,csrf_token,expira_em)
SELECT id,'$RESUMO','csrf-isolado',DATE_ADD(NOW(), INTERVAL 1 DAY)
FROM usuarios WHERE usuario='ana';"

"$SANTAFE_BINARIO" aplicativos/correio/recebedor.fé \
    >"$TEMPORARIO/recebedor.log" 2>&1 &
PROCESSOS+=("$!")
"$SANTAFE_BINARIO" aplicativos/carteiro/carteiro.fé \
    >"$TEMPORARIO/carteiro.log" 2>&1 &
PROCESSOS+=("$!")

for _ in {1..80}; do
    if curl -fsS --max-time 1 \
        "http://127.0.0.1:$PORTA_CARTEIRO/carteiro/estado" >/dev/null 2>&1 &&
       grep -q 'bancos postais, estruturas e segurança prontos' "$TEMPORARIO/recebedor.log"; then
        break
    fi
    sleep 0.1
done
curl -fsS --max-time 2 \
    "http://127.0.0.1:$PORTA_CARTEIRO/carteiro/estado" >/dev/null
grep -q 'bancos postais, estruturas e segurança prontos' "$TEMPORARIO/recebedor.log"

echo "==> Recebedor provisiona destinatário antes do primeiro acesso"
TESTE_SMTP_PORTA="$PORTA_RECEBEDOR" \
TESTE_SMTP_DESTINATARIO='bia@santafé.dev.br' \
    "$SANTAFE_BINARIO" testes/integracao/enviar_correio_local.fé
[[ "$("${ADMIN[@]}" -e \
    "SELECT COUNT(*) FROM correio_caixas WHERE parte_local='bia'")" == 1 ]]
[[ "$("${ADMIN[@]}" -e \
    "SELECT COUNT(*) FROM correio_cartas m JOIN correio_caixas c ON c.id=m.caixa_id WHERE c.parte_local='bia'")" == 1 ]]
[[ "$("${ADMIN[@]}" -e \
    "SELECT COUNT(*) FROM correio_cartas m JOIN correio_caixas c ON c.id=m.caixa_id WHERE c.parte_local='bia' AND m.classificacao_triagem='regular' AND m.pontuacao_suspeita=0")" == 1 ]]

echo "==> Carta recebida aparece no Carteiro com anexo"
TESTE_SMTP_PORTA="$PORTA_RECEBEDOR" \
TESTE_SMTP_DESTINATARIO='ana@santafé.dev.br' \
TESTE_SMTP_ASSUNTO='Carta visível no Carteiro' \
TESTE_SMTP_TEXTO='Recebedor, CD, depósito, MariaDB e Carteiro estão integrados.' \
    "$SANTAFE_BINARIO" testes/integracao/enviar_correio_local.fé
read -r CARTA ANEXO <<< "$("${ADMIN[@]}" -e \
    "SELECT m.id,a.id FROM correio_cartas m JOIN correio_caixas c ON c.id=m.caixa_id JOIN correio_anexos a ON a.carta_id=m.id WHERE c.parte_local='ana' ORDER BY m.id DESC LIMIT 1")"
curl -fsS --max-time 3 -H "Cookie: sf_sessao=$BILHETE" \
    "http://127.0.0.1:$PORTA_CARTEIRO/carteiro/entrada" \
    >"$TEMPORARIO/lista.html"
curl -fsS --max-time 3 -H "Cookie: sf_sessao=$BILHETE" \
    "http://127.0.0.1:$PORTA_CARTEIRO/carteiro/mensagens/$CARTA" \
    >"$TEMPORARIO/carta.html"
curl -fsS --max-time 3 -H "Cookie: sf_sessao=$BILHETE" \
    "http://127.0.0.1:$PORTA_CARTEIRO/carteiro/mensagens/$CARTA/anexos/$ANEXO" \
    >"$TEMPORARIO/anexo.txt"
grep -q 'Carta visível no Carteiro' "$TEMPORARIO/lista.html"
grep -q 'Recebedor, CD, depósito, MariaDB e Carteiro estão integrados' \
    "$TEMPORARIO/carta.html"
grep -q 'depósito íntegro' "$TEMPORARIO/anexo.txt"

# A consulta de conversas usa somente as cartas sintéticas recebidas acima.
"$SANTAFE_BINARIO" testes/bibc/teste_carteiro_conversas_mariadb.fé

echo "==> Triagem pessoal, precedência e histórico reais"
curl -fsS --max-time 5 -o /dev/null \
    -H "Cookie: sf_sessao=$BILHETE" \
    --data-urlencode 'csrf=csrf-isolado' \
    --data-urlencode 'escopo=domínio' \
    --data-urlencode 'valor=exemplo.org' \
    --data-urlencode 'decisão=separar' \
    "http://127.0.0.1:$PORTA_CARTEIRO/carteiro/triagem/regras"
curl -fsS --max-time 5 -o /dev/null \
    -H "Cookie: sf_sessao=$BILHETE" \
    --data-urlencode 'csrf=csrf-isolado' \
    --data-urlencode 'escopo=endereço' \
    --data-urlencode 'valor=maria@exemplo.org' \
    --data-urlencode 'decisão=permitir' \
    "http://127.0.0.1:$PORTA_CARTEIRO/carteiro/triagem/regras"

TESTE_SMTP_PORTA="$PORTA_RECEBEDOR" \
TESTE_SMTP_DESTINATARIO='ana@santafé.dev.br' \
TESTE_SMTP_REMETENTE='maria@exemplo.org' \
TESTE_SMTP_ASSUNTO='Regra exata permitiu' \
    "$SANTAFE_BINARIO" testes/integracao/enviar_correio_local.fé
TESTE_SMTP_PORTA="$PORTA_RECEBEDOR" \
TESTE_SMTP_DESTINATARIO='ana@santafé.dev.br' \
TESTE_SMTP_REMETENTE='outra@exemplo.org' \
TESTE_SMTP_ASSUNTO='Regra de domínio separou' \
    "$SANTAFE_BINARIO" testes/integracao/enviar_correio_local.fé

[[ "$("${ADMIN[@]}" -e \
    "SELECT COUNT(*) FROM correio_cartas m JOIN correio_caixas c ON c.id=m.caixa_id WHERE c.parte_local='ana' AND m.assunto='Regra exata permitiu' AND m.pasta='entrada' AND m.decisao_usuario='regular' AND m.regra_triagem='endereco:maria@exemplo.org' AND m.pontuacao_suspeita=0")" == 1 ]]
[[ "$("${ADMIN[@]}" -e \
    "SELECT COUNT(*) FROM correio_cartas m JOIN correio_caixas c ON c.id=m.caixa_id WHERE c.parte_local='ana' AND m.assunto='Regra de domínio separou' AND m.pasta='indesejadas' AND m.decisao_usuario='indesejada' AND m.regra_triagem='dominio:exemplo.org' AND m.pontuacao_suspeita=0")" == 1 ]]

CARTA_PERMITIDA="$("${ADMIN[@]}" -e \
    "SELECT m.id FROM correio_cartas m JOIN correio_caixas c ON c.id=m.caixa_id WHERE c.parte_local='ana' AND m.assunto='Regra exata permitiu' ORDER BY m.id DESC LIMIT 1")"
curl -fsS --max-time 5 -o /dev/null \
    -H "Cookie: sf_sessao=$BILHETE" \
    --data-urlencode 'csrf=csrf-isolado' \
    --data-urlencode 'decisão=indesejada' \
    "http://127.0.0.1:$PORTA_CARTEIRO/carteiro/mensagens/$CARTA_PERMITIDA/triagem"
[[ "$("${ADMIN[@]}" -e \
    "SELECT COUNT(*) FROM correio_cartas WHERE id=$CARTA_PERMITIDA AND pasta='indesejadas' AND decisao_usuario='indesejada' AND pontuacao_suspeita=0")" == 1 ]]
curl -fsS --max-time 5 -o /dev/null \
    -H "Cookie: sf_sessao=$BILHETE" \
    --data-urlencode 'csrf=csrf-isolado' \
    --data-urlencode 'decisão=regular' \
    "http://127.0.0.1:$PORTA_CARTEIRO/carteiro/mensagens/$CARTA_PERMITIDA/triagem"
[[ "$("${ADMIN[@]}" -e \
    "SELECT COUNT(*) FROM correio_cartas WHERE id=$CARTA_PERMITIDA AND pasta='entrada' AND decisao_usuario='regular' AND pontuacao_suspeita=0")" == 1 ]]
[[ "$("${ADMIN[@]}" -e \
    "SELECT COUNT(*) FROM correio_historico_triagem")" -ge 4 ]]

echo "==> Anexo executável inofensivo vai para Indesejadas"
TESTE_SMTP_PORTA="$PORTA_RECEBEDOR" \
TESTE_SMTP_DESTINATARIO='ana@santafé.dev.br' \
TESTE_SMTP_REMETENTE='anexo@seguro.invalid' \
TESTE_SMTP_ASSUNTO='Anexo executável inofensivo' \
TESTE_SMTP_ANEXO_NOME='nota.pdf.exe' \
TESTE_SMTP_ANEXO_TIPO='application/x-dosexec' \
    "$SANTAFE_BINARIO" testes/integracao/enviar_correio_local.fé
[[ "$("${ADMIN[@]}" -e \
    "SELECT COUNT(*) FROM correio_cartas m JOIN correio_caixas c ON c.id=m.caixa_id WHERE c.parte_local='ana' AND m.assunto='Anexo executável inofensivo' AND m.pasta='indesejadas' AND m.classificacao_triagem='indesejada' AND m.pontuacao_suspeita>=8 AND m.motivos_triagem LIKE '%anexo-executável%'")" == 1 ]]

echo "==> Fisgada mascarada vai para Indesejadas com explicação"
TESTE_SMTP_PORTA="$PORTA_RECEBEDOR" \
TESTE_SMTP_DESTINATARIO='ana@santafé.dev.br' \
TESTE_SMTP_REMETENTE='segurança@banco-exemplo.net' \
TESTE_SMTP_ASSUNTO='Ação urgente: confirme sua conta' \
TESTE_SMTP_TEXTO='Confirme sua senha imediatamente na ligação informada.' \
TESTE_SMTP_HTML='<p>Confirme sua senha imediatamente.</p><a href="https://acesso-hostil.example/entrar">https://banco-exemplo.net/entrar</a>' \
    "$SANTAFE_BINARIO" testes/integracao/enviar_correio_local.fé
[[ "$("${ADMIN[@]}" -e \
    "SELECT COUNT(*) FROM correio_cartas m JOIN correio_caixas c ON c.id=m.caixa_id WHERE c.parte_local='ana' AND m.assunto='Ação urgente: confirme sua conta' AND m.pasta='indesejadas' AND m.classificacao_triagem='indesejada' AND m.pontuacao_suspeita>=8 AND m.motivos_triagem LIKE '%ligação-mascarada%' AND m.motivos_triagem LIKE '%pedido-de-segredo-com-ligação%'")" == 1 ]]

echo "==> HTML recebido permanece fechado e isolado"
TESTE_SMTP_PORTA="$PORTA_RECEBEDOR" \
TESTE_SMTP_DESTINATARIO='ana@santafé.dev.br' \
TESTE_SMTP_REMETENTE='html@seguro.invalid' \
TESTE_SMTP_ASSUNTO='HTML isolado' \
TESTE_SMTP_HTML='<p>Conteúdo formatado</p><script>document.body.dataset.executou="sim"</script><form action="https://externo.invalid/"><button>Enviar</button></form><img src="https://externo.invalid/rastro.png">' \
    "$SANTAFE_BINARIO" testes/integracao/enviar_correio_local.fé
CARTA_HTML="$("${ADMIN[@]}" -e \
    "SELECT m.id FROM correio_cartas m JOIN correio_caixas c ON c.id=m.caixa_id WHERE c.parte_local='ana' AND m.assunto='HTML isolado' ORDER BY m.id DESC LIMIT 1")"
CODIGO_HTML="$(curl -sS --max-time 5 -o "$TEMPORARIO/html-bloqueado.html" \
    -w '%{http_code}' -H "Cookie: sf_sessao=$BILHETE" \
    "http://127.0.0.1:$PORTA_CARTEIRO/carteiro/mensagens/$CARTA_HTML/corpo-html")"
[[ "$CODIGO_HTML" == 403 ]]
grep -q 'permanece protegida' "$TEMPORARIO/html-bloqueado.html"
curl -fsS --max-time 5 -o /dev/null \
    -H "Cookie: sf_sessao=$BILHETE" \
    --data-urlencode 'csrf=csrf-isolado' \
    "http://127.0.0.1:$PORTA_CARTEIRO/carteiro/mensagens/$CARTA_HTML/remetente/confiar"
curl -fsS --max-time 5 -D "$TEMPORARIO/html-cabeçalhos.txt" \
    -o "$TEMPORARIO/html-isolado.html" \
    -H "Cookie: sf_sessao=$BILHETE" \
    "http://127.0.0.1:$PORTA_CARTEIRO/carteiro/mensagens/$CARTA_HTML/corpo-html?mostrar=1"
grep -qi "content-security-policy:.*script-src 'none'.*connect-src 'none'.*img-src data:.*form-action 'none'" \
    "$TEMPORARIO/html-cabeçalhos.txt"
grep -q '<base target="_blank">' "$TEMPORARIO/html-isolado.html"

curl -fsS --max-time 5 -o /dev/null \
    -H "Cookie: sf_sessao=$BILHETE" \
    --data-urlencode 'csrf=csrf-isolado' \
    --data-urlencode 'escopo=endereço' \
    --data-urlencode 'valor=maria@exemplo.org' \
    "http://127.0.0.1:$PORTA_CARTEIRO/carteiro/triagem/regras/remover"
curl -fsS --max-time 5 -o /dev/null \
    -H "Cookie: sf_sessao=$BILHETE" \
    --data-urlencode 'csrf=csrf-isolado' \
    --data-urlencode 'escopo=domínio' \
    --data-urlencode 'valor=exemplo.org' \
    "http://127.0.0.1:$PORTA_CARTEIRO/carteiro/triagem/regras/remover"
[[ "$("${ADMIN[@]}" -e \
    "SELECT COUNT(*) FROM correio_regras_triagem")" == 0 ]]
grep -q 'carteiro.triagem.regraSalva' "$TEMPORARIO/carteiro.pulso"
grep -q 'carteiro.triagem.decisãoDoUsuário' "$TEMPORARIO/carteiro.pulso"

echo "==> Carteiro, fila e Correio Envios"
export TESTE_SMTP_DESTINO_PORTA="$PORTA_DESTINO"
"$SANTAFE_BINARIO" testes/integracao/servidor_smtp_destino.fé \
    >"$TEMPORARIO/destino.log" 2>&1 &
PROCESSOS+=("$!")
sleep 0.2
curl -fsS --max-time 5 -o /dev/null \
    -H "Cookie: sf_sessao=$BILHETE" \
    --data-urlencode 'csrf=csrf-isolado' \
    --data-urlencode 'para=destino@exemplo.org' \
    --data-urlencode 'assunto=Saída integrada' \
    --data-urlencode 'texto=Esta carta atravessou a fila durável.' \
    "http://127.0.0.1:$PORTA_CARTEIRO/carteiro/enviar"
export CORREIO_ENVIOS_ENDERECO=127.0.0.1
export CORREIO_ENVIOS_MODO=retransmissor
export CORREIO_ENVIOS_PORTA="$PORTA_DESTINO"
export CORREIO_ENVIOS_SEGURANCA=nenhuma
export CORREIO_ENVIOS_NOME=xn--santaf-gva.dev.br
export CORREIO_ENVIOS_VALIDAR_CERTIFICADO=falso
"$SANTAFE_BINARIO" aplicativos/correio/envios.fé
grep -q 'Destino recebeu:' "$TEMPORARIO/destino.log"
[[ "$("${ADMIN[@]}" -e \
    "SELECT COUNT(*) FROM correio_fila WHERE estado='entregue'")" == 1 ]]
[[ "$("${ADMIN[@]}" -e \
    "SELECT COUNT(*) FROM correio_cartas WHERE assunto='Saída integrada' AND estado_entrega='entregue'")" == 1 ]]

echo "==> Aviso final de entrega é local, estruturado e idempotente"
FILA_SAIDA="$("${ADMIN[@]}" -e \
    "SELECT referencia_fila FROM correio_cartas WHERE assunto='Saída integrada' LIMIT 1")"
AGORA="$(date +%s)"
"${ADMIN[@]}" -e "
UPDATE correio_fila SET estado='falhou',ultima_falha='550 5.1.1 destinatário inexistente'
WHERE id=$FILA_SAIDA;
INSERT INTO correio_avisos_entrega
(fila_id,tipo,estado,detalhes,tentativas,proxima_tentativa,criada_em,atualizada_em)
VALUES ($FILA_SAIDA,'falha','pendente',
'{\"destinatários\":[\"destino@exemplo.org\"],\"falha\":\"550 5.1.1 destinatário inexistente\",\"últimaTentativa\":$AGORA,\"tentarAté\":$AGORA}',
0,$AGORA,$AGORA,$AGORA);"
"$SANTAFE_BINARIO" aplicativos/correio/envios.fé
[[ "$("${ADMIN[@]}" -e \
    "SELECT COUNT(*) FROM correio_avisos_entrega WHERE fila_id=$FILA_SAIDA AND tipo='falha' AND estado='entregue' AND carta_id IS NOT NULL")" == 1 ]]
[[ "$("${ADMIN[@]}" -e \
    "SELECT COUNT(*) FROM correio_cartas WHERE direcao='entrada' AND assunto='Falha na entrega: Saída integrada' AND remetente='postmaster@xn--santaf-gva.dev.br'")" == 1 ]]
[[ "$("${ADMIN[@]}" -e \
    "SELECT COUNT(*) FROM correio_cartas WHERE direcao='entrada' AND assunto='Falha na entrega: Saída integrada' AND mime_objeto IS NOT NULL AND texto LIKE '%destino@exemplo.org%'")" == 1 ]]
"$SANTAFE_BINARIO" aplicativos/correio/envios.fé
[[ "$("${ADMIN[@]}" -e \
    "SELECT COUNT(*) FROM correio_cartas WHERE direcao='entrada' AND assunto='Falha na entrega: Saída integrada'")" == 1 ]]

echo "==> Item estruturalmente corrompido entra em quarentena"
"${ADMIN[@]}" -e "
INSERT INTO correio_fila
(direcao,estado,remetente,destinatarios,conteudo,tamanho,tentativas,
 proxima_tentativa,criada_em,atualizada_em)
VALUES ('saída','pendente','quarentena@teste.local','{inválido','mime',4,0,0,$AGORA,$AGORA);"
FILA_CORROMPIDA="$("${ADMIN[@]}" -e \
    "SELECT id FROM correio_fila WHERE remetente='quarentena@teste.local' ORDER BY id DESC LIMIT 1")"
for _ in 1 2 3; do
    if "$SANTAFE_BINARIO" aplicativos/correio/envios.fé; then
        echo "ERRO: item corrompido deveria fazer Envios sinalizar falha" >&2
        exit 1
    fi
    "${ADMIN[@]}" -e \
        "UPDATE correio_fila SET proxima_tentativa=0 WHERE id=$FILA_CORROMPIDA AND estado='pendente';"
done
[[ "$("${ADMIN[@]}" -e \
    "SELECT COUNT(*) FROM correio_fila WHERE id=$FILA_CORROMPIDA AND estado='quarentena' AND falhas_internas=3")" == 1 ]]
"$SANTAFE_BINARIO" testes/bibc/teste_correio_quarentena_mariadb.fé
[[ "$("${ADMIN[@]}" -e \
    "SELECT COUNT(*) FROM correio_fila WHERE id=$FILA_CORROMPIDA AND estado='pendente' AND falhas_internas=0")" == 1 ]]
"${ADMIN[@]}" -e "DELETE FROM correio_fila WHERE id=$FILA_CORROMPIDA;"

echo "==> Retomada depois de interrupção no processamento"
"${ADMIN[@]}" -e "
INSERT INTO correio_fila
(direcao,estado,remetente,destinatarios,conteudo,tamanho,tentativas,
 proxima_tentativa,criada_em,atualizada_em,bilhete,arrendada_ate)
VALUES ('saída','processando','recuperacao@teste.local',
        '[\"destino@exemplo.org\"]','mensagem',8,0,0,$AGORA,$AGORA,
        'reserva-carta-expirada',0);
SET @fila_recuperacao=LAST_INSERT_ID();
INSERT INTO correio_avisos_entrega
(fila_id,tipo,estado,detalhes,tentativas,proxima_tentativa,
 bilhete,arrendada_ate,criada_em,atualizada_em)
VALUES (@fila_recuperacao,'atraso','processando','{\"falha\":\"ensaio\"}',
        0,0,'reserva-aviso-expirada',0,$AGORA,$AGORA);"
"$SANTAFE_BINARIO" testes/bibc/teste_correio_recuperação_mariadb.fé
[[ "$("${ADMIN[@]}" -e \
    "SELECT COUNT(*) FROM correio_fila WHERE remetente='recuperacao@teste.local' AND estado='pendente' AND bilhete IS NULL AND arrendada_ate IS NULL")" == 1 ]]
[[ "$("${ADMIN[@]}" -e \
    "SELECT COUNT(*) FROM correio_avisos_entrega a JOIN correio_fila f ON f.id=a.fila_id WHERE f.remetente='recuperacao@teste.local' AND a.estado='pendente' AND a.bilhete IS NULL AND a.arrendada_ate IS NULL")" == 1 ]]
"${ADMIN[@]}" -e \
    "DELETE FROM correio_fila WHERE remetente='recuperacao@teste.local';"

echo "==> Cópia e restauração integral no ambiente isolado"
BANCO_RESTAURADO=santafe_correio_restaurado
COPIA_SQL="$TEMPORARIO/correio.sql"
COPIA_DEPOSITO="$TEMPORARIO/deposito.tar"
DEPOSITO_RESTAURADO="$TEMPORARIO/depósito-restaurado"
OPCOES_DUMP=(--no-defaults --socket="$SOQUETE" -uroot
    --single-transaction --quick --routines --events --triggers
    --hex-blob --skip-comments --order-by-primary)
"$MARIADB_DUMP" "${OPCOES_DUMP[@]}" santafe_correio_teste > "$COPIA_SQL"
tar -cf "$COPIA_DEPOSITO" -C "$CORREIO_DEPOSITO" .
"${CLIENTE_RAIZ[@]}" -e \
    "DROP DATABASE IF EXISTS $BANCO_RESTAURADO; CREATE DATABASE $BANCO_RESTAURADO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
"${CLIENTE_RAIZ[@]}" "$BANCO_RESTAURADO" < "$COPIA_SQL"
COPIA_RESTAURADA_SQL="$TEMPORARIO/correio-restaurado.sql"
"$MARIADB_DUMP" "${OPCOES_DUMP[@]}" "$BANCO_RESTAURADO" > \
    "$COPIA_RESTAURADA_SQL"
cmp "$COPIA_SQL" "$COPIA_RESTAURADA_SQL"
mkdir -p "$DEPOSITO_RESTAURADO"
tar -xf "$COPIA_DEPOSITO" -C "$DEPOSITO_RESTAURADO"
(cd "$CORREIO_DEPOSITO" &&
    find . -type f -print0 | LC_ALL=C sort -z | xargs -0 shasum -a 256) > \
    "$TEMPORARIO/deposito-origem.sha256"
(cd "$DEPOSITO_RESTAURADO" &&
    find . -type f -print0 | LC_ALL=C sort -z | xargs -0 shasum -a 256) > \
    "$TEMPORARIO/deposito-restaurado.sha256"
cmp "$TEMPORARIO/deposito-origem.sha256" \
    "$TEMPORARIO/deposito-restaurado.sha256"
[[ "$("${CLIENTE_RAIZ[@]}" -N "$BANCO_RESTAURADO" -e \
    "SELECT COUNT(*) FROM correio_migracoes WHERE componente='correio' AND versao BETWEEN 1 AND 11")" == 11 ]]
[[ "$("${CLIENTE_RAIZ[@]}" -N "$BANCO_RESTAURADO" -e \
    "SELECT COUNT(*) FROM correio_migracoes WHERE componente='carteiro' AND versao=2")" == 1 ]]

echo "✅ Correio + MariaDB + Carteiro passaram no ambiente isolado."
