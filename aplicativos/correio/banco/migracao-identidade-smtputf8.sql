-- Santafé: identidade da comunidade e parte local SMTPUTF8.
-- Não altera a versão estrutural do Correio: apenas torna as comparações
-- sensíveis a acentos. A aplicação continua normalizando maiúsculas.

ALTER TABLE usuarios
    MODIFY COLUMN usuario VARCHAR(50)
        CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
    MODIFY COLUMN email VARCHAR(254)
        CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL;

ALTER TABLE correio_caixas
    MODIFY COLUMN parte_local VARCHAR(64)
        CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL;
