# src/2-theme_manager/api/visualizar_temasecategorias.py

from flask import Blueprint, jsonify, g
from src.1-auth.utils.auth_required import login_required

theme_bp = Blueprint('theme_manager', __name__)

@theme_bp.route('/temas', methods=['GET'])
@login_required
def view_temas():
    """
    Primeira rota protegida após o login.
    Retorna dados básicos do usuário e status do módulo.
    """
    user = g.current_user

    return jsonify({
        "mensagem": "Acesso autorizado ao Theme Manager",
        "usuario": {
            "id": user["user_id"],
            "email": user["email"]
        },
        "status": "Theme Manager operacional"
    }), 200
