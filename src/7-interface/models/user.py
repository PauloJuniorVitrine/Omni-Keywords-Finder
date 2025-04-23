from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from src.3_data_base.database_connection import Base

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    email = Column(String(150), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    role = Column(String(50), default='user')
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    def set_password(self, password: str) -> None:
        """
        Gera e armazena o hash da senha.

        :param password: Senha em texto puro
        """
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """
        Verifica se a senha fornecida confere com o hash armazenado.

        :param password: Senha fornecida no login
        :return: True se válida, False se inválida
        """
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict:
        """
        Retorna um dicionário serializável com dados do usuário.

        :return: dict com id, email, role, ativo e data de criação
        """
        return {
            "id": self.id,
            "email": self.email,
            "role": self.role,
            "is_active": bool(self.is_active),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
