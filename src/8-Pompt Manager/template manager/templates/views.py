

from fastapi import APIRouter, Request, Depends, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from prompt_manager.templates_editor.models import TemplatePrompt, CategoriaSemana
from database_connection import get_db
import uuid
from datetime import datetime

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/admin/templates")
def visualizar_templates(request: Request, db: Session = Depends(get_db)):
    templates_prompts = db.query(TemplatePrompt).order_by(TemplatePrompt.criado_em.desc()).all()
    return templates.TemplateResponse("templates/listar.html", {"request": request, "templates": templates_prompts})

@router.get("/admin/templates/novo")
def novo_template_form(request: Request):
    categorias = list(CategoriaSemana)
    return templates.TemplateResponse("templates/novo.html", {"request": request, "categorias": categorias})

@router.post("/admin/templates/novo")
def criar_template_via_form(
    request: Request,
    nome: str = Form(...),
    nicho: str = Form(...),
    categoria: CategoriaSemana = Form(...),
    modelo_texto: str = Form(...),
    descricao: str = Form(""),
    tipo_template: str = Form("geral"),
    db: Session = Depends(get_db)
):
    template = TemplatePrompt(
        id=str(uuid.uuid4()),
        nome=nome,
        nicho=nicho,
        categoria=categoria,
        modelo_texto=modelo_texto,
        descricao=descricao,
        tipo_template=tipo_template,
        criado_em=datetime.utcnow(),
        ativo=True
    )
    db.add(template)
    db.commit()
    return RedirectResponse(url="/admin/templates", status_code=303)

@router.get("/admin/templates/{template_id}/editar")
def editar_template_form(template_id: str, request: Request, db: Session = Depends(get_db)):
    template = db.query(TemplatePrompt).filter_by(id=template_id).first()
    if not template:
        return RedirectResponse(url="/admin/templates", status_code=302)
    categorias = list(CategoriaSemana)
    return templates.TemplateResponse("templates/editar.html", {"request": request, "template": template, "categorias": categorias})

@router.post("/admin/templates/{template_id}/editar")
def salvar_edicao_template(
    template_id: str,
    request: Request,
    nome: str = Form(...),
    nicho: str = Form(...),
    categoria: CategoriaSemana = Form(...),
    tipo_template: str = Form("geral"),
    descricao: str = Form(""),
    modelo_texto: str = Form(...),
    ativo: bool = Form(False),
    db: Session = Depends(get_db)
):
    template = db.query(TemplatePrompt).filter_by(id=template_id).first()
    if not template:
        return RedirectResponse(url="/admin/templates", status_code=302)

    template.nome = nome
    template.nicho = nicho
    template.categoria = categoria
    template.tipo_template = tipo_template
    template.descricao = descricao
    template.modelo_texto = modelo_texto
    template.ativo = ativo

    db.commit()
    return RedirectResponse(url="/admin/templates", status_code=303)
