-- Estrutura postal v11: autor visível e remetente do envelope SMTP distintos.

ALTER TABLE correio_cartas
    ADD COLUMN IF NOT EXISTS remetente_envelope VARCHAR(512) NULL
        AFTER remetente;

INSERT IGNORE INTO correio_migracoes (componente, versao)
VALUES ('correio', 11);
