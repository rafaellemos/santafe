-- Correio Santafé, migração 2: depósito híbrido.
--
-- Esta migração altera somente o esquema. Os LONGBLOBs existentes são
-- preservados e continuam legíveis; novas cartas passam a usar os campos de
-- objeto. A migração do conteúdo antigo pode ser executada separadamente.

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
