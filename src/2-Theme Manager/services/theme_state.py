# /theme_manager/services/theme_state.py
from sqlalchemy.orm import Session
from theme_manager.models.tema import Tema
from theme_manager.models.nicho import Nicho
from theme_manager.database import get_db  # função que retorna uma sessão SQLAlchemy
from typing import TypedDict, Optional
import logging

logger = logging.getLogger("theme_state")

class TemaContexto(TypedDict):
    tema: Optional[str]
    nicho: Optional[str]

def get_tema_e_nicho_ativos(db: Optional[Session] = None) -> TemaContexto:
    """
    Retorna o tema ativo e seu respectivo nicho.
    Exemplo:
    {
        "tema": "Conversão",
        "nicho": "Marketing Digital"
    }
    """
    try:
        db = db or next(get_db())

        tema_ativo = db.query(Tema).filter(Tema.ativo == True).order_by(Tema.updated_at.desc()).first()
        if not tema_ativo:
            logger.warning("theme_state.no_active_theme")
            return {"tema": None, "nicho": None}

        nicho = db.query(Nicho).filter(Nicho.id == tema_ativo.nicho_id).first()
        if not nicho:
            logger.warning("theme_state.nicho_not_found")
            return {"tema": tema_ativo.descricao, "nicho": None}

        return {
            "tema": tema_ativo.descricao,
            "nicho": nicho.nome
        }

    except Exception as e:
        logger.error(f"theme_state.erro: {e}")
        return {"tema": None, "nicho": None}
