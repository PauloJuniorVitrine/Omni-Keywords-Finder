# src/2-theme_manager/api/inserir_tema.py

from flask import Blueprint, request, jsonify, g
from src.1-auth.utils.auth_required import login_required
from src.2-theme_manager.models.tema import TemaModel
from src.2-theme_manager.database import db
from datetime import datetime
import logging

tema_bp = Blueprint('inserir_tema', __name__)
logger = logging.getLogger(__name__)

@tema_bp.route('/temas/inserir', methods=['POST'])
@login_required
def inserir_tema():
    """
    Endpoint para inserir um novo tema.
    Protegido por autenticação JWT.
    """
    user = g.current_user
    data = request.get_json()

    # Validação de campos obrigatórios
    campos_obrigatorios = ["nicho", "tema", "categoria", "data_inicio", "data_entrega"]
    faltando = [campo for campo in campos_obrigatorios if campo not in data]

    if faltando:
        return jsonify({
            "erro": "Campos obrigatórios ausentes.",
            "faltando": faltando
        }), 400

    # Validação de datas
    try:
        data_inicio = datetime.strptime(data["data_inicio"], "%Y-%m-%d")
        data_entrega = datetime.strptime(data["data_entrega"], "%Y-%m-%d")
    except ValueError:
        return jsonify({"erro": "Formato de data inválido. Use YYYY-MM-DD."}), 400

    # Persistência real no banco de dados
    try:
        novo_tema = TemaModel(
            descricao=data["tema"],
            categoria=data["categoria"],
            data_inicio=data_inicio,
            data_entrega=data_entrega,
            usuario_id=user["user_id"],
            nicho_id=data["nicho"]  # Assumindo que o valor já é um ID válido
        )
        db.session.add(novo_tema)
        db.session.commit()

        logger.info(f"[InserirTema] Usuário {user['email']} inseriu tema no banco: {data['tema']}")

        return jsonify({
            "mensagem": "Tema inserido com sucesso.",
            "tema_id": novo_tema.id
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao inserir tema no banco: {e}")
        return jsonify({"erro": "Erro interno ao inserir tema."}), 500
