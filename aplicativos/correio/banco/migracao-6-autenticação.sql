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
