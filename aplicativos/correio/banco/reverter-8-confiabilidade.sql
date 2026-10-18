-- Reversão estrutural da v8. Execute apenas depois de parar Envios e
-- confirmar que nenhum aviso ainda precisa ser preservado.

DELETE FROM correio_migracoes
WHERE componente='correio' AND versao=8;

DROP TABLE IF EXISTS correio_avisos_entrega;

ALTER TABLE correio_fila
    DROP COLUMN IF EXISTS falhas_internas;
