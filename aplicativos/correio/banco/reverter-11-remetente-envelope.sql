-- Reversão estrutural da separação de remetentes. Antes de executar, os
-- valores históricos devem ser restaurados pela cópia da publicação.

DELETE FROM correio_migracoes
WHERE componente='correio' AND versao=11;

ALTER TABLE correio_cartas
    DROP COLUMN IF EXISTS remetente_envelope;
