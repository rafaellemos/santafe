-- Retirada controlada da estrutura IMAP v9.
-- Use somente junto da restauração do fonte v8 e com os serviços postais
-- parados. As cartas permanecem; apenas UIDs e estado IMAP são removidos.

DELETE FROM correio_migracoes
WHERE componente='correio' AND versao=9;

DROP TABLE IF EXISTS correio_pastas_imap;

ALTER TABLE correio_cartas
    DROP INDEX IF EXISTS uq_correio_carta_uid_imap,
    DROP COLUMN IF EXISTS uid_imap;
