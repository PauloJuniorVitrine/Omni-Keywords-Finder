# theme_manager/scheduler/agendador.py

import datetime
from sqlalchemy.orm import Session, joinedload
from theme_manager.database import engine
from theme_manager.models.categoria import Categoria
from theme_manager.models.tema import Tema
from theme_manager.models.nicho import Nicho

def get_dia_semana_atual() -> str:
    """Retorna o dia da semana atual no formato compatível com o banco."""
    dias = ['segunda', 'terca', 'quarta', 'quinta', 'sexta', 'sabado', 'domingo']
    return dias[datetime.datetime.now().weekday()]

def simular_coleta(nicho: str, tema: str, categoria: str) -> None:
    """Simula a execução de coleta para determinada categoria."""
    print(f"[🔍] Coletando dados para: Nicho='{nicho}' | Tema='{tema}' | Categoria='{categoria}'")

def agendar_coletas():
    """
    Executa coletas para as categorias agendadas para o dia atual.
    """

    dia_atual = get_dia_semana_atual()
    print(f"📅 Executando agendador para: {dia_atual.upper()}")

    with Session(engine) as session:
        categorias = (
            session.query(Categoria)
            .options(joinedload(Categoria.tema).joinedload(Tema.nicho))
            .filter(Categoria.dia_semana == dia_atual, Categoria.ativo == True)
            .all()
        )

        if not categorias:
            print("[ℹ️] Nenhuma categoria ativa agendada para hoje.")
            return

        for categoria in categorias:
            tema = categoria.tema
            nicho = tema.nicho
            simular_coleta(nicho.nome, tema.descricao, categoria.descricao)
