# theme_manager/models/nicho.py

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base, validates

Base = declarative_base()

class TimestampMixin:
    """Mixin que adiciona timestamps de criação e atualização."""
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Nicho(Base, TimestampMixin):
    """
    Modelo representando um nicho de conteúdo.

    Atributos:
        id (int): Identificador único do nicho.
        nome (str): Nome único do nicho.
        created_at (datetime): Timestamp de criação.
        updated_at (datetime): Timestamp da última modificação.
    """
    __tablename__ = 'nichos'

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(100), unique=True, nullable=False, index=True)

    def __init__(self, nome: str) -> None:
        self.nome = self.validate_nome(nome)

    @validates('nome')
    def validate_nome(self, key: str, nome: str) -> str:
        if not nome or not nome.strip():
            raise ValueError("O nome do nicho não pode estar vazio ou em branco.")
        return nome.strip()

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "nome": self.nome,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<Nicho(id={self.id}, nome='{self.nome}')>"
