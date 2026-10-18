-- Correio Santafé, migração 7: Triagem pessoal e auditável por caixa.

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
