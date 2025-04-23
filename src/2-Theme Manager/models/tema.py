# theme_manager/models/tema.py

from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Index
from sqlalchemy.orm import declarative_base, relationship, validates
from .base import TimestampMixin
from .nicho import Nicho

Base = declarative_base()

class Tema(Base, TimestampMixin):
    """
    Modelo representando um tema associado a um nicho.

    Atributos:
        id (int): Identificador único do tema.
        descricao (str): Descrição do tema.
        nicho_id (int): ID do nicho associado (chave estrangeira).
        ativo (bool): Flag de controle de soft delete.
        created_at (datetime): Timestamp de criação.
        updated_at (datetime): Timestamp da última modificação.
    """

    __tablename__ = 'temas'

    id = Column(Integer, primary_key=True, autoincrement=True)
    descricao = Column(String(255), nullable=False)
    nicho_id = Column(Integer, ForeignKey('nichos.id'), nullable=False, index=True)
    ativo = Column(Boolean, default=True)

    nicho = relationship("Nicho", backref="temas")

    def __init__(self, descricao: str, nicho_ref) -> None:
        """
        Permite instanciar o tema com uma descrição e um ID ou objeto de nicho.
        """
        self.descricao = self.validate_descricao(descricao)
        self.nicho_id = self._resolve_nicho_id(nicho_ref)

    def _resolve_nicho_id(self, nicho_ref) -> int:
        if isinstance(nicho_ref, Nicho):
            return nicho_ref.id
        if isinstance(nicho_ref, int) and nicho_ref > 0:
            return nicho_ref
        raise ValueError("nicho_id inválido: deve ser um objeto Nicho ou um inteiro positivo.")

    @validates('descricao')
    def validate_descricao(self, key: str, descricao: str) -> str:
        if not descricao or not descricao.strip():
            raise ValueError("A descrição do tema não pode estar vazia.")
        return descricao.strip()

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "descricao": self.descricao,
            "nicho_id": self.nicho_id,
            "ativo": self.ativo,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Tema":
        """
        Cria uma instância de Tema a partir de um dicionário.
        Espera as chaves: descricao e nicho_id ou nicho.
        """
        descricao = data.get("descricao")
        nicho = data.get("nicho_id") or data.get("nicho")
        return cls(descricao, nicho)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Tema):
            return False
        return self.id == other.id and self.descricao == other.descricao

    def __hash__(self) -> int:
        return hash((self.id, self.descricao))

    def __repr__(self) -> str:
        return (
            f"<Tema(id={self.id}, descricao='{self.descricao}', "
            f"nicho_id={self.nicho_id}, ativo={self.ativo})>"
        )


# Índices adicionais, se necessário
Index("idx_tema_nicho_id", Tema.nicho_id)
