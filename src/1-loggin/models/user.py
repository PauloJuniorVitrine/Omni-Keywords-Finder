# src/1-auth/models/user.py

import sqlite3
import logging
from flask import current_app
from werkzeug.security import check_password_hash

logger = logging.getLogger(__name__)

class UserModel:
    def __init__(self, user_id, email, password_hash):
        self.id = user_id
        self.email = email
        self.password_hash = password_hash

    @classmethod
    def find_by_email(cls, email):
        """
        Busca um usuário pelo e-mail. Retorna uma instância de UserModel ou None.
        """
        try:
            if not email:
                logger.warning("[UserModel] Email vazio fornecido na busca.")
                return None

            email = email.strip().lower()
            if not email:
                logger.warning("[UserModel] Email inválido após sanitização.")
                return None

            # Caminho do banco dinâmico via configuração
            db_path = current_app.config.get("DB_PATH", "src/3-data base/database.db")

            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                query = "SELECT id, email, password_hash FROM users WHERE email = ?"
                cursor.execute(query, (email,))
                result = cursor.fetchone()

            if result:
                logger.info(f"[UserModel] Usuário encontrado: {email}")
                return cls(user_id=result[0], email=result[1], password_hash=result[2])
            else:
                logger.info(f"[UserModel] Nenhum usuário encontrado para o e-mail: {email}")
                return None

        except Exception as e:
            logger.error(f"[UserModel] Erro ao buscar usuário: {e}")
            return None

    def verify_password(self, senha):
        """
        Verifica se a senha fornecida corresponde ao hash armazenado.
        """
        return check_password_hash(self.password_hash, senha)
