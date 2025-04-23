from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field
from typing import Literal
import uuid
import logging
from datetime import datetime
import re
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from prompt_manager.database.models import PromptGerado, Base

# =============================
# LOGGER
# =============================
logger = logging.getLogger("prompt_receiver")
logging.basicConfig(level=logging.INFO)

# =============================
# DATABASE
# =============================
DATABASE_URL = "sqlite:///prompt_manager.db"
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# =============================
# ROUTER
# =============================
router = APIRouter(prefix="/prompt", tags=["Prompt Manager"])

# =============================
# MODELO DE DADOS
# =============================
class PromptPayload(BaseModel):
    palavra_chave: str = Field(..., min_length=3)
    nicho: str
    categoria: Literal[
        "Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"
    ]
    tema: str
    score: float = Field(..., gt=0)
    trace_id: str
    palavras_chave_secundarias: str = Field(default="")

# =============================
# TEMPLATES DE PROMPT
# =============================
prompt_templates = {
    "Segunda": "Escreva um conteúdo sobre '{{palavra_chave}}' com foco em autoridade.",
    "Terça": "Crie um post envolvente sobre '{{palavra_chave}}' que gere compartilhamentos.",
    "Quarta": "Gere um roteiro de vídeo sobre '{{palavra_chave}}' voltado ao nicho de {{nicho}}.",
    "Quinta": "Desenvolva um e-mail persuasivo com o tema '{{palavra_chave}}'.",
    "Sexta": "Crie um artigo otimizado para SEO sobre '{{palavra_chave}}'.",
    "Sábado": "Liste estratégias práticas relacionadas a '{{palavra_chave}}'.",
    "Domingo": "Conte uma história inspiradora envolvendo '{{palavra_chave}}'."
}

def gerar_prompt(palavra_chave: str, categoria: str, nicho: str) -> str:
    template = prompt_templates.get(categoria)
    if not template:
        logger.warning(f"⚠️ Categoria '{categoria}' inválida. Usando fallback.")
        template = "Crie um conteúdo valioso utilizando o termo '{{palavra_chave}}' no nicho de {{nicho}}."
    return template.replace("{{palavra_chave}}", palavra_chave).replace("{{nicho}}", nicho)

# =============================
# ENDPOINT PARA RECEBER PALAVRA-CHAVE
# =============================
@router.post("/receber_palavra")
def receber_palavra(payload: PromptPayload, request: Request, db: Session = Depends(get_db)):
    if not re.match(r"^[\w\s\-]+$", payload.palavra_chave):
        raise HTTPException(status_code=422, detail="Palavra-chave contém caracteres inválidos.")

    prompt_final = gerar_prompt(payload.palavra_chave, payload.categoria, payload.nicho)
    prompt_id = str(uuid.uuid4())
    gerado_em = datetime.utcnow()

    novo_prompt = PromptGerado(
        id=prompt_id,
        prompt=prompt_final,
        palavra_chave_principal=payload.palavra_chave,
        palavras_chave_secundarias=payload.palavras_chave_secundarias,
        nicho=payload.nicho,
        categoria=payload.categoria,
        tema=payload.tema,
        trace_id=payload.trace_id,
        score=payload.score,
        gerado_em=gerado_em,
        origem="pipeline_google"
    )
    db.add(novo_prompt)
    db.commit()

    logger.info(f"✅ Prompt salvo no banco | trace_id={payload.trace_id} | IP={request.client.host}")

    return {
        "status": "ok",
        "prompt_id": prompt_id,
        "prompt": prompt_final,
        "metadata": {
            "nicho": payload.nicho,
            "categoria": payload.categoria,
            "tema": payload.tema,
            "score": payload.score,
            "trace_id": payload.trace_id,
            "gerado_em": gerado_em.isoformat()
        }
    }
