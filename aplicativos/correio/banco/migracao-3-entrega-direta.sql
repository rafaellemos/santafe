-- Entrega direta por MX: registra destinatários recusados definitivamente
-- enquanto os temporários permanecem na fila.
ALTER TABLE correio_fila
    ADD COLUMN IF NOT EXISTS falhas_permanentes LONGTEXT NULL
        AFTER ultima_falha;

INSERT IGNORE INTO correio_migracoes (componente, versao)
VALUES ('correio', 3);
