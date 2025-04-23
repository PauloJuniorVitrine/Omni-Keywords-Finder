# src/2-theme_manager/api/excluir_tema.py

from flask import Blueprint, request, jsonify, g
from src.1-auth.utils.auth_required import login_required
import logging

excluir_bp = Blueprint('excluir_tema', __name__)
logger = logging.getLogger(__name__)

@excluir_bp.route('/temas/excluir/<int:tema_id>', methods=['DELETE'])
@login_required
def excluir_tema(tema_id):
    """
    Endpoint para excluir um tema existente.
    Protegido por autenticação JWT.
    """
    user = g.current_user

    # Simulação da exclusão (em produção, faria delete no banco)
    logger.info(f"[ExcluirTema] Usuário {user['email']} excluiu o tema {tema_id}")

    return jsonify({
        "mensagem": f"Tema {tema_id} excluído com sucesso.",
        "usuario": user["email"]
    }), 200
