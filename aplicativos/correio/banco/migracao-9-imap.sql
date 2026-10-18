-- Correio v8 -> v9: identidade persistente das cartas no IMAP.
--
-- O id interno da carta serviu de ponto de partida para os registros já
-- existentes. A partir desta migração, cada pasta mantém seu próprio próximo
-- UID; ao mover uma carta para outra pasta, o destino atribui um UID novo.

ALTER TABLE correio_cartas
    ADD COLUMN IF NOT EXISTS uid_imap BIGINT UNSIGNED NULL AFTER id;

UPDATE correio_cartas SET uid_imap=id WHERE uid_imap IS NULL;

ALTER TABLE correio_cartas
    MODIFY COLUMN uid_imap BIGINT UNSIGNED NOT NULL,
    ADD UNIQUE KEY IF NOT EXISTS uq_correio_carta_uid_imap
        (caixa_id, pasta, uid_imap);

CREATE TABLE IF NOT EXISTS correio_pastas_imap (
    caixa_id BIGINT UNSIGNED NOT NULL,
    pasta ENUM('entrada', 'enviadas', 'rascunhos', 'indesejadas', 'lixeira')
        NOT NULL,
    validade_uid INT UNSIGNED NOT NULL,
    proximo_uid BIGINT UNSIGNED NOT NULL DEFAULT 1,
    atualizada_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (caixa_id, pasta),
    CONSTRAINT fk_correio_pasta_imap_caixa FOREIGN KEY (caixa_id)
        REFERENCES correio_caixas (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO correio_pastas_imap
    (caixa_id, pasta, validade_uid, proximo_uid)
SELECT c.id, p.pasta, UNIX_TIMESTAMP(),
       COALESCE(MAX(m.uid_imap), 0) + 1
FROM correio_caixas c
JOIN (
    SELECT 'entrada' AS pasta UNION ALL SELECT 'enviadas'
    UNION ALL SELECT 'rascunhos' UNION ALL SELECT 'indesejadas'
    UNION ALL SELECT 'lixeira'
) p
LEFT JOIN correio_cartas m ON m.caixa_id=c.id AND m.pasta=p.pasta
GROUP BY c.id, p.pasta
ON DUPLICATE KEY UPDATE
    proximo_uid=GREATEST(proximo_uid, VALUES(proximo_uid));

INSERT IGNORE INTO correio_migracoes (componente, versao)
VALUES ('correio', 9);
