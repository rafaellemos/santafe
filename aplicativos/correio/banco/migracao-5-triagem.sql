-- Correio Santafé, migração 5: decisão explicável da Triagem.

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
