import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from prompt_manager.database.models import Base

# ==========================
# LOGGING PROFISSIONAL
# ==========================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("setup_database")

# ==========================
# CONFIGURAÇÃO DO BANCO
# ==========================
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///prompt_manager.db")


def get_engine():
    logger.info(f"📡 Conectando ao banco de dados: {DATABASE_URL}")
    return create_engine(DATABASE_URL, echo=False)


def testar_conexao(engine):
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ Conexão com o banco bem-sucedida.")
    except SQLAlchemyError as e:
        logger.error(f"❌ Erro ao conectar ao banco: {e}")
        raise


def criar_schema():
    engine = get_engine()
    testar_conexao(engine)

    logger.info("📦 Criando estrutura do banco de dados...")
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Tabelas criadas com sucesso.")


if __name__ == "__main__":
    criar_schema()
