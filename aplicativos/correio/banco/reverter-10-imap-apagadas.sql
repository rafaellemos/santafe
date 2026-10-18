-- Reversão controlada da persistência de \Deleted da estrutura v10.

DELETE FROM correio_migracoes
WHERE componente='correio' AND versao=10;

ALTER TABLE correio_cartas
    DROP INDEX IF EXISTS ix_correio_carta_apagada_imap,
    DROP COLUMN IF EXISTS apagada_imap;
