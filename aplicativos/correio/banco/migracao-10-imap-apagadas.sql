-- Correio v9 -> v10: torna persistente o sinalizador IMAP \Deleted.
-- Clientes móveis podem marcar uma carta, encerrar a conexão e expurgá-la
-- somente em uma sessão posterior.

ALTER TABLE correio_cartas
    ADD COLUMN IF NOT EXISTS apagada_imap BOOLEAN NOT NULL DEFAULT FALSE
        AFTER importante,
    ADD INDEX IF NOT EXISTS ix_correio_carta_apagada_imap
        (caixa_id, pasta, apagada_imap, uid_imap);

INSERT IGNORE INTO correio_migracoes (componente, versao)
VALUES ('correio', 10);
