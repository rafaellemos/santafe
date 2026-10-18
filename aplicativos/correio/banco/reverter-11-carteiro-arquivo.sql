-- Reversão conservadora do Carteiro v2.
-- Só deve ser usada pelo publicador antes de liberar a nova interface.

UPDATE correio_cartas
SET pasta=IF(direcao='entrada','entrada','enviadas'),
    apagada_imap=FALSE,
    atualizada_em=UNIX_TIMESTAMP()
WHERE pasta='arquivadas';

DELETE FROM correio_pastas_imap WHERE pasta='arquivadas';
DELETE FROM correio_migracoes
WHERE componente='carteiro' AND versao=2;

ALTER TABLE correio_pastas_imap
    MODIFY COLUMN pasta ENUM(
        'entrada', 'enviadas', 'rascunhos',
        'indesejadas', 'lixeira') NOT NULL;

ALTER TABLE correio_cartas
    MODIFY COLUMN pasta ENUM(
        'entrada', 'enviadas', 'rascunhos',
        'indesejadas', 'lixeira') NOT NULL;
