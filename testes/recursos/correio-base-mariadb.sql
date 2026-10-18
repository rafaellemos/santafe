-- Estrutura mínima da identidade usada pelos ensaios isolados do Correio.
-- A produção possui estas tabelas no sfdev; este arquivo nunca deve ser
-- aplicado sobre o banco real.

CREATE TABLE usuarios (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    nome VARCHAR(120) NOT NULL,
    usuario VARCHAR(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
    email VARCHAR(254) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
    senha_hash VARCHAR(255) CHARACTER SET ascii COLLATE ascii_bin
        NOT NULL DEFAULT '',
    papel VARCHAR(32) NOT NULL DEFAULT 'usuário',
    estado VARCHAR(20) NOT NULL DEFAULT 'ativo',
    PRIMARY KEY (id),
    UNIQUE KEY uq_usuario (usuario),
    UNIQUE KEY uq_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE sessoes (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    usuario_id BIGINT UNSIGNED NOT NULL,
    token_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    csrf_token VARCHAR(160) NOT NULL,
    expira_em DATETIME NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_sessao_token (token_hash),
    CONSTRAINT fk_sessao_usuario FOREIGN KEY (usuario_id)
        REFERENCES usuarios (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
