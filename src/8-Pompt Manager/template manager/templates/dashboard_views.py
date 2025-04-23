from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from database_connection import get_db
from prompt_manager.templates_editor.models import TemplatePrompt, CategoriaSemana
from datetime import datetime, date

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/admin/dashboard")
def dashboard_view(request: Request, db: Session = Depends(get_db)):
    total = db.query(func.count(TemplatePrompt.id)).scalar()
    ativos = db.query(func.count()).filter(TemplatePrompt.ativo == True).scalar()
    inativos = db.query(func.count()).filter(TemplatePrompt.ativo == False).scalar()

    hoje = db.query(func.count()).filter(
        func.date(TemplatePrompt.criado_em) == date.today()
    ).scalar()

    por_categoria = dict(
        db.query(TemplatePrompt.categoria, func.count(TemplatePrompt.id))
          .group_by(TemplatePrompt.categoria).all()
    )

    por_nicho = dict(
        db.query(TemplatePrompt.nicho, func.count(TemplatePrompt.id))
          .group_by(TemplatePrompt.nicho).all()
    )

    ultimos = db.query(TemplatePrompt).order_by(desc(TemplatePrompt.criado_em)).limit(5).all()

    return templates.TemplateResponse("templates/dashboard.html", {
        "request": request,
        "total": total,
        "ativos": ativos,
        "inativos": inativos,
        "hoje": hoje,
        "por_categoria": {c.value: n for c, n in por_categoria.items()},
        "por_nicho": por_nicho,
        "ultimos": ultimos,
        "now": datetime.now()
    })
