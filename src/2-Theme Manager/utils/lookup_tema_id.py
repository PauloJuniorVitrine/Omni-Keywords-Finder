from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound
from sqlalchemy import func
from theme_manager.models.nicho import Nicho
from theme_manager.models.tema import Tema
from database_connection import cache  # Redis opcional
import logging

logger = logging.getLogger("theme_lookup")

def get_id_tema(session: Session, nome_nicho: str, nome_tema: str, criar_se_nao_existir: bool = False, trace_id: str = None) -> int:
    """
    Retorna o ID do tema com base no nome do nicho e do tema. Cria o tema se permitido.

    Args:
        session (Session): Sessão SQLAlchemy ativa.
        nome_nicho (str): Nome do nicho.
        nome_tema (str): Nome do tema vinculado ao nicho.
        criar_se_nao_existir (bool): Se True, cria o tema automaticamente.
        trace_id (str): Opcional. ID de rastreamento para logging contextual.

    Returns:
        int: ID do tema se encontrado ou criado.

    Raises:
        ValueError: Se nicho ou tema não forem encontrados e criação não for permitida.
    """
    nome_nicho = nome_nicho.strip().lower()
    nome_tema = nome_tema.strip().lower()
    cache_key = f"id_tema:{nome_nicho}:{nome_tema}"

    if cache:
        cached = cache.get(cache_key)
        if cached:
            return int(cached)

    try:
        nicho = session.query(Nicho).filter(func.lower(Nicho.nome) == nome_nicho).one()
    except NoResultFound:
        logger.error(f"[get_id_tema] Nicho '{nome_nicho}' não encontrado | trace_id={trace_id}")
        raise ValueError(f"Nicho '{nome_nicho}' não encontrado.")

    try:
        tema = session.query(Tema).filter(
            func.lower(Tema.nome) == nome_tema,
            Tema.nicho_id == nicho.id
        ).one()
    except NoResultFound:
        if criar_se_nao_existir:
            tema = Tema(nome=nome_tema, nicho_id=nicho.id)
            session.add(tema)
            session.commit()
            logger.info(f"[get_id_tema] Tema '{nome_tema}' criado automaticamente no nicho '{nome_nicho}' | trace_id={trace_id}")
        else:
            logger.error(f"[get_id_tema] Tema '{nome_tema}' não encontrado no nicho '{nome_nicho}' | trace_id={trace_id}")
            raise ValueError(f"Tema '{nome_tema}' não encontrado no nicho '{nome_nicho}'.")

    # Cachear resultado
    if cache:
        cache.set(cache_key, tema.id, ex=3600)  # 1 hora

    return tema.id
