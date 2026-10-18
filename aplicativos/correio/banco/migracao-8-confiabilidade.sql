-- Correio v7 -> v8: avisos de estado e quarentena operacional.

ALTER TABLE correio_fila
    ADD COLUMN IF NOT EXISTS falhas_internas INT UNSIGNED NOT NULL DEFAULT 0
        AFTER falhas_permanentes;

CREATE TABLE IF NOT EXISTS correio_avisos_entrega (
    fila_id BIGINT UNSIGNED NOT NULL,
    tipo ENUM('atraso', 'falha') NOT NULL,
    estado ENUM('pendente', 'processando', 'entregue', 'cancelado', 'quarentena')
        NOT NULL DEFAULT 'pendente',
    detalhes LONGTEXT NOT NULL,
    tentativas INT UNSIGNED NOT NULL DEFAULT 0,
    proxima_tentativa BIGINT NOT NULL DEFAULT 0,
    ultima_falha TEXT NULL,
    bilhete VARCHAR(80) NULL,
    arrendada_ate BIGINT NULL,
    carta_id BIGINT UNSIGNED NULL,
    criada_em BIGINT NOT NULL,
    atualizada_em BIGINT NOT NULL,
    PRIMARY KEY (fila_id, tipo),
    UNIQUE KEY uq_correio_aviso_bilhete (bilhete),
    KEY ix_correio_aviso_estado
        (estado, proxima_tentativa, fila_id, tipo),
    KEY ix_correio_aviso_carta (carta_id),
    CONSTRAINT fk_correio_aviso_fila FOREIGN KEY (fila_id)
        REFERENCES correio_fila (id) ON DELETE CASCADE,
    CONSTRAINT fk_correio_aviso_carta FOREIGN KEY (carta_id)
        REFERENCES correio_cartas (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO correio_migracoes (componente, versao)
VALUES ('correio', 8);
