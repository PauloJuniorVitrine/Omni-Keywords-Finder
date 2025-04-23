# theme_manager/models/categoria.py

from datetime import datetime, time
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Time, Index
from sqlalchemy.orm import declarative_base, relationship, validates
from .base import TimestampMixin
from .tema import Tema
import logging

Base = declarative_base()
logger = logging.getLogger("categoria_model")

class Categoria(Base, TimestampMixin):
    """
    Modelo representando uma categoria vinculada a um tema.

    Atributos:
        id (int): Identificador único da categoria.
        tema_id (int): Chave estrangeira para a tabela de temas.
        nome (str): Nome da categoria.
        dia_semana (str): Dia da semana para execução.
        hora_execucao (time): Horário de execução.
        data_inicio_coleta (datetime): Início do ciclo de coleta.
        data_entrega_resultado (datetime): Data de entrega final.
    """

    __tablename__ = 'categorias'

    id = Column(Integer, primary_key=True, autoincrement=True)
    tema_id = Column(Integer, ForeignKey('temas.id'), nullable=False, index=True)
    nome = Column(String(100), nullable=False)
    dia_semana = Column(String(15), nullable=False)
    hora_execucao = Column(Time, nullable=False)
    data_inicio_coleta = Column(DateTime, nullable=False)
    data_entrega_resultado = Column(DateTime, nullable=False)

    tema = relationship("Tema", backref="categorias")

    __table_args__ = (
        Index("idx_categoria_tema_dia", "tema_id", "dia_semana"),
    )

    DIAS_VALIDOS = ['segunda', 'terca', 'quarta', 'quinta', 'sexta', 'sabado', 'domingo']

    @validates('dia_semana')
    def valida_dia_semana(self, key, dia: str) -> str:
        if dia.lower() not in self.DIAS_VALIDOS:
            raise ValueError(f"Dia da semana inválido: {dia}")
        return dia.lower()

    @validates('hora_execucao')
    def valida_hora(self, key, valor: time) -> time:
        if not isinstance(valor, time):
            raise ValueError("hora_execucao deve ser um objeto datetime.time válido")
        return valor

    @validates('data_inicio_coleta', 'data_entrega_resultado')
    def valida_datas(self, key, valor: datetime) -> datetime:
        if not isinstance(valor, datetime):
            raise ValueError(f"{key} deve ser um datetime válido")
        return valor

    def is_executavel_today(self, data_referencia=None) -> bool:
        """
        Verifica se a categoria está agendada para hoje e dentro da janela de coleta.
        """
        hoje = (data_referencia or datetime.utcnow()).date()
        hoje_nome = (data_referencia or datetime.utcnow()).strftime('%A').lower()

        if hoje_nome != self.dia_semana:
            return False

        if not (self.data_inicio_coleta.date() <= hoje <= self.data_entrega_resultado.date()):
            logger.info(f"⛔ Categoria '{self.nome}' fora da janela de coleta. Hoje: {hoje}, Início: {self.data_inicio_coleta}, Fim: {self.data_entrega_resultado}")
            return False

        return True

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "tema_id": self.tema_id,
            "nome": self.nome,
            "dia_semana": self.dia_semana,
            "hora_execucao": self.hora_execucao.strftime('%H:%M') if self.hora_execucao else None,
            "data_inicio_coleta": self.data_inicio_coleta.isoformat() if self.data_inicio_coleta else None,
            "data_entrega_resultado": self.data_entrega_resultado.isoformat() if self.data_entrega_resultado else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self) -> str:
        return (
            f"<Categoria(id={self.id}, nome='{self.nome}', tema_id={self.tema_id}, "
            f"dia_semana='{self.dia_semana}', hora_execucao='{self.hora_execucao}')>"
        )
