# theme_manager/forms/form_editar_tema.py

import logging
import click
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from theme_manager.models.tema import Tema
from theme_manager.models.nicho import Nicho
from theme_manager.database import engine
from theme_manager.utils.validator import limpar_entrada

# Configuração de logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')


def buscar_tema_por_id(session: Session, tema_id: int) -> Tema | None:
    """Busca tema por ID."""
    return session.query(Tema).filter_by(id=tema_id).first()


def buscar_tema_por_nome_e_nicho(session: Session, tema_desc: str, nicho_nome: str) -> Tema | None:
    """Busca tema por descrição + nome do nicho."""
    nicho = session.query(Nicho).filter_by(nome=nicho_nome).first()
    if not nicho:
        raise ValueError(f"Nicho '{nicho_nome}' não encontrado.")
    return session.query(Tema).filter_by(descricao=tema_desc, nicho_id=nicho.id).first()


def editar_tema_por_objeto(session: Session, tema: Tema, nova_descricao: str, confirmar: bool = True) -> None:
    """
    Atualiza a descrição de um tema já existente, com confirmação opcional.
    """
    if not nova_descricao.strip() or nova_descricao == tema.descricao:
        raise ValueError("A nova descrição é inválida ou igual à atual.")

    if confirmar:
        click.echo(f"\n[⚠️] Tema atual: {tema.descricao}")
        click.echo(f"[➡️] Nova descrição: {nova_descricao}")
        if not click.confirm("Confirmar alteração?"):
            click.echo("❎ Edição cancelada.")
            return

    tema_antiga = tema.descricao
    tema.descricao = nova_descricao.strip()
    session.commit()

    logger.info(f"Tema ID {tema.id} atualizado de '{tema_antiga}' para '{nova_descricao}'")
    click.echo(f"[✔] Tema atualizado com sucesso.")


@click.command()
@click.option('--id', 'tema_id', type=int, help='ID do tema a editar.')
@click.option('--tema', type=str, help='Descrição atual do tema.')
@click.option('--nicho', type=str, help='Nome do nicho correspondente.')
@click.option('--nova-descricao', prompt=True, help='Nova descrição para o tema.')
@click.option('--forcar', is_flag=True, default=False, help='Pula a confirmação e aplica direto.')
def editar_tema(tema_id: int, tema: str, nicho: str, nova_descricao: str, forcar: bool):
    """
    Edita a descrição de um tema existente via CLI, com suporte a ID ou (tema + nicho).
    """

    try:
        with Session(engine) as session:
            tema_obj = None

            if tema_id:
                tema_obj = buscar_tema_por_id(session, tema_id)
            elif tema and nicho:
                tema_obj = buscar_tema_por_nome_e_nicho(session, tema, nicho)
            else:
                raise ValueError("Você deve informar --id OU --tema + --nicho.")

            if not tema_obj:
                click.echo("[❌] Tema não encontrado.")
                return

            editar_tema_por_objeto(session, tema_obj, nova_descricao, confirmar=not forcar)

    except ValueError as ve:
        click.echo(f"[ERRO] Entrada inválida: {ve}")
    except SQLAlchemyError as se:
        click.echo(f"[ERRO] Erro no banco de dados: {se}")
    except Exception as e:
        click.echo(f"[ERRO] Erro inesperado: {e}")
