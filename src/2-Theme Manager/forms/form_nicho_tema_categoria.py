

# theme_manager/forms/form_nicho_tema_categoria.py

import sys
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from theme_manager.models.nicho import Nicho
from theme_manager.models.tema import Tema
from theme_manager.models.categoria import Categoria, DIAS_SEMANA_VALIDOS
from theme_manager.database import engine
from theme_manager.utils.validator import limpar_entrada

Base = Nicho.__bases__[0]  # Assume herança comum do declarative_base()

def obter_entrada_usuario() -> tuple:
    """Coleta os dados via CLI com limpeza básica."""
    print("=== Inserção de Nicho > Tema > Categoria ===")
    nicho_nome = limpar_entrada(input("Digite o nome do nicho: "))
    tema_descricao = limpar_entrada(input("Digite a descrição do tema: "))
    categoria_descricao = limpar_entrada(input("Digite a descrição da categoria: "))
    dia_semana = limpar_entrada(input("Digite o dia da semana (segunda a domingo): ")).lower()

    if dia_semana not in DIAS_SEMANA_VALIDOS:
        raise ValueError(f"Dia da semana inválido: '{dia_semana}'")

    return nicho_nome, tema_descricao, categoria_descricao, dia_semana


def inserir_nicho_tema_categoria():
    """Insere Nicho, Tema e Categoria com vínculo completo no banco de dados."""

    try:
        nicho_nome, tema_desc, categoria_desc, dia_semana = obter_entrada_usuario()

        with Session(engine) as session:
            # Buscar ou criar Nicho
            nicho = session.query(Nicho).filter_by(nome=nicho_nome).first()
            if not nicho:
                nicho = Nicho(nicho_nome)
                session.add(nicho)
                session.commit()
                print(f"[✔] Nicho criado: {nicho.nome}")
            else:
                print(f"[ℹ️] Nicho encontrado: {nicho.nome}")

            # Buscar ou criar Tema
            tema = session.query(Tema).filter_by(descricao=tema_desc, nicho_id=nicho.id).first()
            if not tema:
                tema = Tema(tema_desc, nicho.id)
                session.add(tema)
                session.commit()
                print(f"[✔] Tema criado: {tema.descricao} (Nicho: {nicho.nome})")
            else:
                print(f"[ℹ️] Tema encontrado: {tema.descricao}")

            # Criar Categoria
            categoria = Categoria(categoria_desc, tema.id, dia_semana)
            session.add(categoria)
            session.commit()
            print(f"[✔] Categoria '{categoria.descricao}' vinculada ao tema '{tema.descricao}' para '{categoria.dia_semana}'")

    except ValueError as ve:
        print(f"[ERRO] Entrada inválida: {ve}")
        sys.exit(1)
    except SQLAlchemyError as e:
        print(f"[ERRO] Erro no banco de dados: {e}")
        sys.exit(2)
    except Exception as e:
        print(f"[ERRO] Erro inesperado: {e}")
        sys.exit(99)
