
# setup_database.py — Enterprise Plus++
# Inicialização resiliente e logada do banco global centralizado com sistema de cache

import sqlite3
from pathlib import Path
from datetime import datetime
import logging
import sys
import shelve

# === Configurações ===
BASE_DIR = Path(".")
DB_PATH = BASE_DIR / "global_keywords.db"
LOG_PATH = BASE_DIR / "logs"
CACHE_PATH = BASE_DIR / ".cache/setup_cache.db"
LOG_PATH.mkdir(parents=True, exist_ok=True)
CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)

# === Logger ===
log_file = LOG_PATH / f"setup_database_{datetime.now().strftime('%Y%m%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("setup_database")

# === SQL da tabela principal ===
CREATE_TABELA_SQL = """
CREATE TABLE IF NOT EXISTS palavras_chave (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    origem TEXT NOT NULL,
    tema TEXT NOT NULL,
    palavra TEXT NOT NULL,
    tags TEXT,
    escore REAL,
    validado INTEGER,
    trace_id TEXT,
    criado_em TEXT,
    fonte TEXT DEFAULT '',
    metodo_geracao TEXT DEFAULT ''
);
"""

# === Auditoria / Versão do esquema ===
CREATE_SCHEMA_VERSAO_SQL = """
CREATE TABLE IF NOT EXISTS schema_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    versao TEXT NOT NULL,
    criado_em TEXT NOT NULL
);
"""

INSERIR_VERSAO_SQL = """
INSERT INTO schema_info (versao, criado_em)
VALUES (?, ?)
"""

VERSAO_ATUAL = "1.0.0-enterprise"

def usar_cache():
    with shelve.open(str(CACHE_PATH)) as cache:
        return cache.get("setup_realizado") == VERSAO_ATUAL

def salvar_cache():
    with shelve.open(str(CACHE_PATH)) as cache:
        cache["setup_realizado"] = VERSAO_ATUAL

def inicializar_banco():
    if usar_cache():
        logger.info("⏩ Setup já realizado anteriormente. Cache válido.")
        return
    try:
        with sqlite3.connect(DB_PATH) as conn:
            logger.info("🧱 Criando tabelas...")
            conn.execute(CREATE_TABELA_SQL)
            conn.execute(CREATE_SCHEMA_VERSAO_SQL)
            conn.execute(INSERIR_VERSAO_SQL, (VERSAO_ATUAL, datetime.utcnow().isoformat()))
        salvar_cache()
        logger.info("✅ Tabelas criadas com sucesso e cache salvo.")
    except Exception as e:
        logger.error(f"❌ Falha na criação das tabelas: {e}")
        raise

def main():
    logger.info("🚀 Iniciando setup do banco de dados unificado (Enterprise Plus++)...")
    inicializar_banco()
    logger.info("🏁 Setup concluído com sucesso.")

if __name__ == "__main__":
    main()
