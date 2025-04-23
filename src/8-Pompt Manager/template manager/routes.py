from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from prompt_manager.templates_editor.models import TemplatePrompt, CategoriaSemana
from database_connection import get_db

router = APIRouter(prefix="/templates", tags=["Templates"])

# =========================
# SCHEMAS Pydantic
# =========================
class TemplateBase(BaseModel):
    nome: str
    nicho: str
    categoria: CategoriaSemana
    modelo_texto: str
    descricao: Optional[str] = ""
    tipo_template: Optional[str] = "geral"

class TemplateCreate(TemplateBase):
    pass

class TemplateUpdate(TemplateBase):
    ativo: Optional[bool] = True

class TemplateResponse(TemplateBase):
    id: str
    ativo: bool
    criado_em: datetime

    class Config:
        orm_mode = True

# =========================
# ENDPOINTS CRUD
# =========================
@router.get("/", response_model=List[TemplateResponse], summary="Listar templates", description="Retorna todos os templates com filtros opcionais por nicho, categoria, ativo e suporte a paginação.")
def listar_templates(
    db: Session = Depends(get_db),
    nicho: Optional[str] = Query(None),
    categoria: Optional[CategoriaSemana] = Query(None),
    ativo: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=100)
):
    query = db.query(TemplatePrompt)
    if nicho:
        query = query.filter(TemplatePrompt.nicho == nicho)
    if categoria:
        query = query.filter(TemplatePrompt.categoria == categoria)
    if ativo is not None:
        query = query.filter(TemplatePrompt.ativo == ativo)
    return query.offset(skip).limit(limit).all()

@router.get("/{template_id}", response_model=TemplateResponse)
def buscar_template(template_id: str, db: Session = Depends(get_db)):
    template = db.query(TemplatePrompt).filter_by(id=template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template não encontrado")
    return template

@router.post("/", response_model=TemplateResponse)
def criar_template(data: TemplateCreate, db: Session = Depends(get_db)):
    novo = TemplatePrompt(**data.dict())
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return novo

@router.put("/{template_id}", response_model=TemplateResponse)
def atualizar_template(template_id: str, data: TemplateUpdate, db: Session = Depends(get_db)):
    template = db.query(TemplatePrompt).filter_by(id=template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template não encontrado")

    campos_protegidos = ["id", "criado_em", "arquivo_origem"]
    for field, value in data.dict().items():
        if field not in campos_protegidos:
            setattr(template, field, value)
    db.commit()
    db.refresh(template)
    return template

@router.patch("/{template_id}/toggle", response_model=TemplateResponse)
def ativar_ou_desativar_template(template_id: str, db: Session = Depends(get_db)):
    template = db.query(TemplatePrompt).filter_by(id=template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template não encontrado")

    template.ativo = not template.ativo
    db.commit()
    db.refresh(template)
    return template

@router.delete("/{template_id}")
def excluir_template(template_id: str, db: Session = Depends(get_db)):
    template = db.query(TemplatePrompt).filter_by(id=template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template não encontrado")

    db.delete(template)
    db.commit()
    return {
        "status": "ok",
        "removido": template.id,
        "nome": template.nome
    }
