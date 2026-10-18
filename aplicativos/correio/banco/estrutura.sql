-- Correio Santafé: depósito postal sobre usuarios e sessoes do sfdev.
-- Execute no mesmo banco definido por SANTAFE_MARIADB_BANCO.

CREATE TABLE IF NOT EXISTS correio_migracoes (
    componente VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    versao INT UNSIGNED NOT NULL,
    aplicada_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (componente, versao)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS correio_caixas (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    usuario_id BIGINT UNSIGNED NOT NULL,
    parte_local VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
    dominio_ascii VARCHAR(253) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    endereco_exibido VARCHAR(254) NOT NULL,
    nome_exibido VARCHAR(120) NOT NULL,
    estado ENUM('ativa', 'bloqueada', 'excluida') NOT NULL DEFAULT 'ativa',
    cota_tacos BIGINT UNSIGNED NOT NULL DEFAULT 1073741824,
    uso_tacos BIGINT UNSIGNED NOT NULL DEFAULT 0,
    criada_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizada_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_correio_caixa_usuario (usuario_id),
    UNIQUE KEY uq_correio_caixa_endereco (parte_local, dominio_ascii),
    KEY ix_correio_caixa_estado (estado),
    CONSTRAINT fk_correio_caixa_usuario FOREIGN KEY (usuario_id)
        REFERENCES usuarios (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Migração idempotente para uma instalação criada antes da contabilização.
ALTER TABLE correio_caixas
    ADD COLUMN IF NOT EXISTS uso_tacos BIGINT UNSIGNED NOT NULL DEFAULT 0
        AFTER cota_tacos;

-- A parte local SMTPUTF8 é comparada exatamente. A aplicação já
-- converte maiúsculas em minúsculas; a collation binária conserva a
-- diferença semântica entre, por exemplo, "jose" e "josé".
ALTER TABLE correio_caixas
    MODIFY COLUMN parte_local VARCHAR(64)
        CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL;

CREATE TABLE IF NOT EXISTS correio_cartas (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    uid_imap BIGINT UNSIGNED NULL,
    caixa_id BIGINT UNSIGNED NOT NULL,
    direcao ENUM('entrada', 'saida') NOT NULL,
    pasta ENUM('entrada', 'enviadas', 'rascunhos', 'arquivadas', 'indesejadas', 'lixeira') NOT NULL,
    identificacao VARCHAR(998) NULL,
    remetente VARCHAR(512) NOT NULL,
    remetente_envelope VARCHAR(512) NULL,
    destinatarios LONGTEXT NOT NULL,
    assunto VARCHAR(998) NOT NULL DEFAULT '',
    resumo VARCHAR(300) NOT NULL DEFAULT '',
    texto MEDIUMTEXT NULL,
    html MEDIUMTEXT NULL,
    mime LONGBLOB NULL,
    mime_objeto CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL,
    tamanho BIGINT UNSIGNED NOT NULL,
    lida BOOLEAN NOT NULL DEFAULT FALSE,
    importante BOOLEAN NOT NULL DEFAULT FALSE,
    apagada_imap BOOLEAN NOT NULL DEFAULT FALSE,
    estado_entrega ENUM('recebida', 'rascunho', 'pendente', 'processando', 'entregue', 'falhou') NOT NULL,
    falha_entrega TEXT NULL,
    referencia_fila BIGINT UNSIGNED NULL,
    criada_em BIGINT NOT NULL,
    atualizada_em BIGINT NOT NULL,
    responder_para VARCHAR(512) NULL,
    classificacao_triagem ENUM('regular', 'suspeita', 'indesejada')
        NOT NULL DEFAULT 'regular',
    pontuacao_suspeita SMALLINT UNSIGNED NOT NULL DEFAULT 0,
    motivos_triagem LONGTEXT NULL,
    resultado_spf VARCHAR(24) CHARACTER SET ascii COLLATE ascii_bin NULL,
    resultado_dkim VARCHAR(24) CHARACTER SET ascii COLLATE ascii_bin NULL,
    resultado_dmarc VARCHAR(24) CHARACTER SET ascii COLLATE ascii_bin NULL,
    dominio_autor VARCHAR(253) CHARACTER SET ascii COLLATE ascii_bin NULL,
    politica_dmarc VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NULL,
    acao_dmarc VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_correio_carta_uid_imap (caixa_id, pasta, uid_imap),
    KEY ix_correio_carta_pasta (caixa_id, pasta, criada_em, id),
    KEY ix_correio_carta_nao_lida (caixa_id, pasta, lida, criada_em),
    KEY ix_correio_carta_apagada_imap
        (caixa_id, pasta, apagada_imap, uid_imap),
    KEY ix_correio_carta_identificacao (caixa_id, identificacao(191)),
    KEY ix_correio_carta_fila (referencia_fila),
    KEY ix_correio_carta_objeto (mime_objeto),
    FULLTEXT KEY ft_correio_carta (remetente, assunto, resumo, texto),
    CONSTRAINT fk_correio_carta_caixa FOREIGN KEY (caixa_id)
        REFERENCES correio_caixas (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS correio_pastas_imap (
    caixa_id BIGINT UNSIGNED NOT NULL,
    pasta ENUM('entrada', 'enviadas', 'rascunhos', 'arquivadas', 'indesejadas', 'lixeira')
        NOT NULL,
    validade_uid INT UNSIGNED NOT NULL,
    proximo_uid BIGINT UNSIGNED NOT NULL DEFAULT 1,
    atualizada_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (caixa_id, pasta),
    CONSTRAINT fk_correio_pasta_imap_caixa FOREIGN KEY (caixa_id)
        REFERENCES correio_caixas (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS correio_anexos (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    carta_id BIGINT UNSIGNED NOT NULL,
    nome VARCHAR(255) NOT NULL,
    tipo VARCHAR(255) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    tamanho BIGINT UNSIGNED NOT NULL,
    dados LONGBLOB NULL,
    dados_objeto CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL,
    PRIMARY KEY (id),
    KEY ix_correio_anexo_carta (carta_id, id),
    KEY ix_correio_anexo_objeto (dados_objeto),
    CONSTRAINT fk_correio_anexo_carta FOREIGN KEY (carta_id)
        REFERENCES correio_cartas (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Fila de transporte usada por correio.filaMariaDB. A biblioteca também
-- sabe criá-la; mantê-la aqui torna a implantação auditável e repetível.
CREATE TABLE IF NOT EXISTS correio_fila (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    direcao VARCHAR(12) NOT NULL,
    estado VARCHAR(20) NOT NULL,
    remetente VARCHAR(254) NOT NULL,
    destinatarios LONGTEXT NOT NULL,
    conteudo LONGBLOB NULL,
    conteudo_objeto CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL,
    tamanho BIGINT UNSIGNED NOT NULL,
    tentativas INT UNSIGNED NOT NULL DEFAULT 0,
    proxima_tentativa BIGINT NOT NULL DEFAULT 0,
    criada_em BIGINT NOT NULL,
    atualizada_em BIGINT NOT NULL,
    ultima_falha TEXT NULL,
    falhas_permanentes LONGTEXT NULL,
    bilhete VARCHAR(80) NULL,
    arrendada_ate BIGINT NULL,
    PRIMARY KEY (id),
    KEY correio_estado_proxima (estado, proxima_tentativa, id),
    KEY correio_fila_objeto (conteudo_objeto),
    UNIQUE KEY correio_bilhete (bilhete)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO correio_migracoes (componente, versao)
VALUES ('correio', 1);

-- Migração v2: objetos binários novos ficam no depósito durável. As
-- colunas LONGBLOB tornam-se opcionais para que registros v1 continuem
-- legíveis enquanto a migração dos dados antigos é feita em segundo plano.
ALTER TABLE correio_cartas
    MODIFY COLUMN mime LONGBLOB NULL,
    ADD COLUMN IF NOT EXISTS mime_objeto
        CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL AFTER mime,
    ADD INDEX IF NOT EXISTS ix_correio_carta_objeto (mime_objeto);

ALTER TABLE correio_anexos
    MODIFY COLUMN dados LONGBLOB NULL,
    ADD COLUMN IF NOT EXISTS dados_objeto
        CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL AFTER dados,
    ADD INDEX IF NOT EXISTS ix_correio_anexo_objeto (dados_objeto);

ALTER TABLE correio_fila
    MODIFY COLUMN conteudo LONGBLOB NULL,
    ADD COLUMN IF NOT EXISTS conteudo_objeto
        CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL AFTER conteudo,
    ADD INDEX IF NOT EXISTS correio_fila_objeto (conteudo_objeto);

INSERT IGNORE INTO correio_migracoes (componente, versao)
VALUES ('correio', 2);

-- Migração v3: a entrega direta pode concluir alguns domínios e adiar
-- outros. A fila preserva destinatários recusados definitivamente para que
-- novas tentativas não dupliquem cartas já aceitas.
ALTER TABLE correio_fila
    ADD COLUMN IF NOT EXISTS falhas_permanentes LONGTEXT NULL
        AFTER ultima_falha;

INSERT IGNORE INTO correio_migracoes (componente, versao)
VALUES ('correio', 3);

-- Migração v4: conserva Reply-To/From normalizado para respostas do Carteiro.
ALTER TABLE correio_cartas
    ADD COLUMN IF NOT EXISTS responder_para VARCHAR(512) NULL
        AFTER atualizada_em;

INSERT IGNORE INTO correio_migracoes (componente, versao)
VALUES ('correio', 4);

-- Migração v5: decisão explicável da Triagem.
ALTER TABLE correio_cartas
    ADD COLUMN IF NOT EXISTS classificacao_triagem
        ENUM('regular', 'suspeita', 'indesejada') NOT NULL DEFAULT 'regular'
        AFTER responder_para,
    ADD COLUMN IF NOT EXISTS pontuacao_suspeita
        SMALLINT UNSIGNED NOT NULL DEFAULT 0 AFTER classificacao_triagem,
    ADD COLUMN IF NOT EXISTS motivos_triagem LONGTEXT NULL
        AFTER pontuacao_suspeita,
    ADD INDEX IF NOT EXISTS ix_correio_carta_triagem
        (caixa_id, classificacao_triagem, pontuacao_suspeita);

INSERT IGNORE INTO correio_migracoes (componente, versao)
VALUES ('correio', 5);

-- Migração v6: autenticação postal de entrada, separada da Triagem.
ALTER TABLE correio_cartas
    ADD COLUMN IF NOT EXISTS resultado_spf
        VARCHAR(24) CHARACTER SET ascii COLLATE ascii_bin NULL AFTER motivos_triagem,
    ADD COLUMN IF NOT EXISTS resultado_dkim
        VARCHAR(24) CHARACTER SET ascii COLLATE ascii_bin NULL AFTER resultado_spf,
    ADD COLUMN IF NOT EXISTS resultado_dmarc
        VARCHAR(24) CHARACTER SET ascii COLLATE ascii_bin NULL AFTER resultado_dkim,
    ADD COLUMN IF NOT EXISTS dominio_autor
        VARCHAR(253) CHARACTER SET ascii COLLATE ascii_bin NULL AFTER resultado_dmarc,
    ADD COLUMN IF NOT EXISTS politica_dmarc
        VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NULL AFTER dominio_autor,
    ADD COLUMN IF NOT EXISTS acao_dmarc
        VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NULL AFTER politica_dmarc;

INSERT IGNORE INTO correio_migracoes (componente, versao)
VALUES ('correio', 6);

-- Estrutura v1 do Carteiro: preferências de confiança particulares de cada caixa.
-- A confiança nunca carrega conteúdo externo sozinha; apenas permite que o
-- usuário confirme esse carregamento em uma carta.
CREATE TABLE IF NOT EXISTS correio_remetentes_confiaveis (
    caixa_id BIGINT UNSIGNED NOT NULL,
    endereco VARCHAR(512) NOT NULL,
    criada_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizada_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (caixa_id, endereco),
    CONSTRAINT fk_correio_remetente_confiavel_caixa FOREIGN KEY (caixa_id)
        REFERENCES correio_caixas (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO correio_migracoes (componente, versao)
VALUES ('carteiro', 1);

-- Migração v7: preferências pessoais da Triagem, decisão por carta e
-- histórico de auditoria. A classificação automática original é preservada.
ALTER TABLE correio_cartas
    ADD COLUMN IF NOT EXISTS decisao_usuario
        ENUM('nenhuma', 'regular', 'indesejada') NOT NULL DEFAULT 'nenhuma'
        AFTER acao_dmarc,
    ADD COLUMN IF NOT EXISTS regra_triagem VARCHAR(600) NULL
        AFTER decisao_usuario,
    ADD COLUMN IF NOT EXISTS decidida_em BIGINT NULL
        AFTER regra_triagem;

CREATE TABLE IF NOT EXISTS correio_regras_triagem (
    caixa_id BIGINT UNSIGNED NOT NULL,
    escopo ENUM('endereco', 'dominio') NOT NULL,
    valor VARCHAR(512) NOT NULL,
    decisao ENUM('permitir', 'separar') NOT NULL,
    criada_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizada_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (caixa_id, escopo, valor),
    KEY ix_correio_regra_triagem_decisao (caixa_id, decisao, atualizada_em),
    CONSTRAINT fk_correio_regra_triagem_caixa FOREIGN KEY (caixa_id)
        REFERENCES correio_caixas (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS correio_historico_triagem (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    caixa_id BIGINT UNSIGNED NOT NULL,
    carta_id BIGINT UNSIGNED NULL,
    acao ENUM(
        'marcou_regular', 'marcou_indesejada',
        'regra_permitir', 'regra_separar', 'regra_removida'
    ) NOT NULL,
    escopo ENUM('endereco', 'dominio') NULL,
    valor VARCHAR(512) NULL,
    criada_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY ix_correio_historico_triagem_caixa (caixa_id, criada_em, id),
    CONSTRAINT fk_correio_historico_triagem_caixa FOREIGN KEY (caixa_id)
        REFERENCES correio_caixas (id) ON DELETE CASCADE,
    CONSTRAINT fk_correio_historico_triagem_carta FOREIGN KEY (carta_id)
        REFERENCES correio_cartas (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO correio_migracoes (componente, versao)
VALUES ('correio', 7);

-- Migração v8: avisos idempotentes de atraso/falha e quarentena
-- operacional para itens irrecuperáveis da fila.
ALTER TABLE correio_fila
    ADD COLUMN IF NOT EXISTS falhas_internas INT UNSIGNED NOT NULL DEFAULT 0
        AFTER falhas_permanentes;

CREATE TABLE IF NOT EXISTS correio_avisos_entrega (
    fila_id BIGINT UNSIGNED NOT NULL,
    tipo ENUM('atraso', 'falha') NOT NULL,
    estado ENUM('pendente', 'processando', 'entregue', 'cancelado', 'quarentena')
        NOT NULL DEFAULT 'pendente',
    detalhes LONGTEXT NOT NULL,
    tentativas INT UNSIGNED NOT NULL DEFAULT 0,
    proxima_tentativa BIGINT NOT NULL DEFAULT 0,
    ultima_falha TEXT NULL,
    bilhete VARCHAR(80) NULL,
    arrendada_ate BIGINT NULL,
    carta_id BIGINT UNSIGNED NULL,
    criada_em BIGINT NOT NULL,
    atualizada_em BIGINT NOT NULL,
    PRIMARY KEY (fila_id, tipo),
    UNIQUE KEY uq_correio_aviso_bilhete (bilhete),
    KEY ix_correio_aviso_estado
        (estado, proxima_tentativa, fila_id, tipo),
    KEY ix_correio_aviso_carta (carta_id),
    CONSTRAINT fk_correio_aviso_fila FOREIGN KEY (fila_id)
        REFERENCES correio_fila (id) ON DELETE CASCADE,
    CONSTRAINT fk_correio_aviso_carta FOREIGN KEY (carta_id)
        REFERENCES correio_cartas (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO correio_migracoes (componente, versao)
VALUES ('correio', 8);

-- Migração v9: UIDs persistentes e estado das pastas IMAP. As tabelas e
-- colunas já fazem parte da definição inicial acima; este marcador mantém a
-- mesma versão observável das instalações atualizadas por migração.
ALTER TABLE correio_cartas
    MODIFY COLUMN uid_imap BIGINT UNSIGNED NOT NULL;

INSERT IGNORE INTO correio_migracoes (componente, versao)
VALUES ('correio', 9);

-- Migração v10: \Deleted persiste entre conexões IMAP. O Carteiro
-- omite cartas marcadas enquanto EXPUNGE, UID EXPUNGE ou CLOSE conclui a
-- operação solicitada pelo cliente.
ALTER TABLE correio_cartas
    ADD COLUMN IF NOT EXISTS apagada_imap BOOLEAN NOT NULL DEFAULT FALSE
        AFTER importante,
    ADD INDEX IF NOT EXISTS ix_correio_carta_apagada_imap
        (caixa_id, pasta, apagada_imap, uid_imap);

INSERT IGNORE INTO correio_migracoes (componente, versao)
VALUES ('correio', 10);

-- Migração v11: separa o autor visível do cabeçalho From do remetente
-- técnico do envelope SMTP. Transportadores podem substituir MAIL FROM por
-- um endereço de retorno próprio, que não deve aparecer ao leitor.
ALTER TABLE correio_cartas
    ADD COLUMN IF NOT EXISTS remetente_envelope VARCHAR(512) NULL
        AFTER remetente;

INSERT IGNORE INTO correio_migracoes (componente, versao)
VALUES ('correio', 11);

-- Carteiro v2: arquivo postal real. "Todas" é uma visão virtual e não
-- duplica cartas; Arquivadas é uma pasta física também visível pelo IMAP.
ALTER TABLE correio_cartas
    MODIFY COLUMN pasta ENUM(
        'entrada', 'enviadas', 'rascunhos', 'arquivadas',
        'indesejadas', 'lixeira') NOT NULL;

ALTER TABLE correio_pastas_imap
    MODIFY COLUMN pasta ENUM(
        'entrada', 'enviadas', 'rascunhos', 'arquivadas',
        'indesejadas', 'lixeira') NOT NULL;

INSERT IGNORE INTO correio_migracoes (componente, versao)
VALUES ('carteiro', 2);
