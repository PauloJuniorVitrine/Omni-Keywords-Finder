# src/2-theme_manager/api/editar_tema.py

from flask import Blueprint, request, jsonify, g
from src.1-auth.utils.auth_required import login_required
import logging

editar_bp = Blueprint('editar_tema', __name__)
logger = logging.getLogger(__name__)

@editar_bp.route('/temas/editar/<int:tema_id>', methods=['PUT'])
@login_required
def editar_tema(tema_id):
    """
    Endpoint para editar um tema existente.
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

    # Simulação de edição no banco (placeholder)
    tema_editado = {
        "id": tema_id,
        "nicho": data["nicho"],
        "tema": data["tema"],
        "categoria": data["categoria"],
        "data_inicio": data["data_inicio"],
        "data_entrega": data["data_entrega"],
        "usuario_id": user["user_id"]
    }

    # Log da operação
    logger.info(f"[EditarTema] Usuário {user['email']} editou o tema {tema_id}: {tema_editado}")

    return jsonify({
        "mensagem": f"Tema {tema_id} editado com sucesso.",
        "tema": tema_editado
    }), 200
