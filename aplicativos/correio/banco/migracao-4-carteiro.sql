-- Correio Santafé, migração 4: endereço de resposta do Carteiro.

ALTER TABLE correio_cartas
    ADD COLUMN IF NOT EXISTS responder_para VARCHAR(512) NULL
        AFTER atualizada_em;

INSERT IGNORE INTO correio_migracoes (componente, versao)
VALUES ('correio', 4);
