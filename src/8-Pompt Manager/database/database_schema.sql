-- 📌 Criar esquema do banco de dados compatível com toda a estrutura desenvolvida
-- Banco de dados: PostgreSQL

-- 🔹 Criar Extensão para Criptografia
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 🔹 Criar Tabela de Usuários
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    mfa_secret TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 🔹 Criar Tabela de Tokens JWT
CREATE TABLE tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token TEXT NOT NULL,
    is_refresh BOOLEAN DEFAULT FALSE,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 🔹 Criar Tabela de Blacklist de Tokens
CREATE TABLE token_blacklist (
    id SERIAL PRIMARY KEY,
    token TEXT UNIQUE NOT NULL,
    revoked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 🔹 Criar Tabela de Logs de Acesso
CREATE TABLE access_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 🔹 Criar Tabela de Configuração do Sistema
CREATE TABLE system_config (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(255) UNIQUE NOT NULL,
    config_value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 🔹 Criar Tabela de Sessões Ativas
CREATE TABLE active_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    session_token TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

-- 🔹 Criar Tabela de Auditoria
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(255) NOT NULL,
    operation VARCHAR(10) NOT NULL, -- INSERT, UPDATE, DELETE
    record_id INTEGER NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 🔹 Criar Triggers para Auditoria
CREATE OR REPLACE FUNCTION audit_changes() RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_logs (table_name, operation, record_id, user_id)
    VALUES (TG_TABLE_NAME, TG_OP, NEW.id, NEW.user_id);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_users
AFTER INSERT OR UPDATE OR DELETE ON users
FOR EACH ROW EXECUTE FUNCTION audit_changes();

CREATE TRIGGER audit_tokens
AFTER INSERT OR UPDATE OR DELETE ON tokens
FOR EACH ROW EXECUTE FUNCTION audit_changes();

-- 🔹 Criar Procedure para Logout Seguro
CREATE OR REPLACE FUNCTION revoke_token(p_token TEXT) RETURNS VOID AS $$
BEGIN
    INSERT INTO token_blacklist (token) VALUES (p_token);
END;
$$ LANGUAGE plpgsql;

-- 🔹 Criar Procedure para Excluir Tokens Expirados
CREATE OR REPLACE FUNCTION cleanup_expired_tokens() RETURNS VOID AS $$
BEGIN
    DELETE FROM tokens WHERE expires_at < NOW();
    DELETE FROM token_blacklist WHERE revoked_at < NOW() - INTERVAL '7 days';
END;
$$ LANGUAGE plpgsql;

-- 🔹 Criar Particionamento da Tabela de Logs
CREATE TABLE access_logs_2024 PARTITION OF access_logs
FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

-- 🔹 Criar Índices e Otimizações
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_tokens_expires ON tokens(expires_at);
CREATE INDEX idx_logs_user ON access_logs(user_id);
CREATE INDEX idx_blacklist_token ON token_blacklist(token);

-- 🔹 Criar Stored Procedure para Recuperação de Configurações do Sistema
CREATE OR REPLACE FUNCTION get_config(p_key TEXT) RETURNS TEXT AS $$
DECLARE
    config_value TEXT;
BEGIN
    SELECT config_value INTO config_value FROM system_config WHERE config_key = p_key;
    RETURN config_value;
END;
$$ LANGUAGE plpgsql;

-- 🔹 Criar Cache de Configuração no Redis
-- Esse recurso será implementado via aplicação para otimizar consultas frequentes
