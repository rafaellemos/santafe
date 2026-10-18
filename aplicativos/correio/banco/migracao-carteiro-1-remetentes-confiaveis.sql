-- Carteiro Santafé, estrutura 1: remetentes confiáveis por caixa.

CREATE TABLE IF NOT EXISTS correio_remetentes_confiaveis (
    caixa_id BIGINT UNSIGNED NOT NULL,
    endereco VARCHAR(512) NOT NULL,
    criada_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizada_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (caixa_id, endereco),
    CONSTRAINT fk_correio_remetente_confiavel_caixa FOREIGN KEY (caixa_id)
        REFERENCES correio_caixas (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO correio_migracoes (componente, versao)
VALUES ('carteiro', 1);
