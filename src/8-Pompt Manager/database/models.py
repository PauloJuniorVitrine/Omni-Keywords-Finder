from sqlalchemy import Column, String, Float, DateTime, Index
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

class PromptGerado(Base):
    __tablename__ = "prompts_gerados"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    prompt = Column(String(2000), nullable=False)
    palavra_chave_principal = Column(String(255), nullable=False)
    palavras_chave_secundarias = Column(String(1000), nullable=True)  # Lista separada por vírgulas
    nicho = Column(String(100), nullable=False)
    categoria = Column(String(50), nullable=False)
    tema = Column(String(255), nullable=False)
    trace_id = Column(String(100), nullable=False)
    score = Column(Float, nullable=False)
    gerado_em = Column(DateTime, default=datetime.utcnow)
    origem = Column(String(100), default="pipeline_google")

    __table_args__ = (
        Index('ix_prompts_trace_id', 'trace_id'),
        Index('ix_prompts_nicho', 'nicho'),
        Index('ix_prompts_categoria', 'categoria'),
        Index('ix_prompts_gerado_em', 'gerado_em'),
    )

    def get_secundarias_como_lista(self):
        return [p.strip() for p in self.palavras_chave_secundarias.split(',')] if self.palavras_chave_secundarias else []

    def __repr__(self):
        return f"<PromptGerado(palavra='{self.palavra_chave_principal}', nicho='{self.nicho}', categoria='{self.categoria}')>"
