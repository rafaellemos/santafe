-- Carteiro v2: arquivo postal físico e visão virtual "Todas".
-- Esta migração altera somente o contrato versionado do Carteiro; a versão
-- postal principal é administrada pelas migrações do Correio.

ALTER TABLE correio_cartas
    MODIFY COLUMN pasta ENUM(
        'entrada', 'enviadas', 'rascunhos', 'arquivadas',
        'indesejadas', 'lixeira') NOT NULL;

ALTER TABLE correio_pastas_imap
    MODIFY COLUMN pasta ENUM(
        'entrada', 'enviadas', 'rascunhos', 'arquivadas',
        'indesejadas', 'lixeira') NOT NULL;

INSERT IGNORE INTO correio_migracoes (componente, versao)
VALUES ('carteiro', 2);
