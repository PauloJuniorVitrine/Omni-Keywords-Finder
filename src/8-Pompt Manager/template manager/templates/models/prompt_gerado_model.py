from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid
import enum

Base = declarative_base()

class CategoriaSemana(enum.Enum):
    Segunda = "Segunda"
    Terca = "Terça"
    Quarta = "Quarta"
    Quinta = "Quinta"
    Sexta = "Sexta"
    Sabado = "Sábado"
    Domingo = "Domingo"

class PromptGerado(Base):
    __tablename__ = "prompts_gerados"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    template_id = Column(String, ForeignKey("templates_prompts.id"), nullable=False)
    palavra_chave = Column(String(255), nullable=False)
    palavra_secundaria = Column(String(255), nullable=True)
    texto_gerado = Column(Text(length=10000), nullable=False)
    nicho = Column(String(100), nullable=False)
    categoria = Column(Enum(CategoriaSemana), nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow, index=True)

    template = relationship("TemplatePrompt", backref="prompts_gerados")

    def __repr__(self):
        return f"<PromptGerado(id={self.id}, nicho={self.nicho}, categoria={self.categoria.value})>"
