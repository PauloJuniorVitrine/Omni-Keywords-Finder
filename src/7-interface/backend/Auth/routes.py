import time
import logging
from flask import Blueprint, request, jsonify
from src.3_data_base.database_connection import Session
from src.7_interface.backend.models.user import User
from src.7_interface.backend.auth.utils import generate_token, get_token_from_header
from src.7_interface.backend.auth.blacklist import add_to_blacklist
from src.7_interface.backend.auth.decorators import login_required

logger = logging.getLogger(__name__)
auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Autentica o usuário e retorna um token JWT.
    Requer JSON com email e senha.
    """
    try:
        if not request.is_json:
            return jsonify({"status": "error", "message": "Requisição deve estar no formato JSON"}), 415

        data = request.get_json()

        if not data or "email" not in data or "password" not in data:
            return jsonify({"status": "error", "message": "Email e senha são obrigatórios"}), 400

        session = Session()
        user = session.query(User).filter_by(email=data["email"]).first()

        if not user or not user.check_password(data["password"]):
            logger.warning(f"Tentativa de login falhou para email: {data.get('email')}")
            time.sleep(0.5)  # Anti-brute-force leve
            return jsonify({"status": "error", "message": "Credenciais inválidas"}), 401

        if not user.is_active:
            logger.warning(f"Usuário desativado tentou login: {user.email}")
            return jsonify({"status": "error", "message": "Usuário desativado"}), 403

        token = generate_token(user.id)
        logger.info(f"Login bem-sucedido: {user.email}")

        return jsonify({"status": "success", "data": {"token": token}}), 200

    except Exception as e:
        logger.error(f"Erro interno no login: {str(e)}")
        return jsonify({"status": "error", "message": "Erro interno no servidor"}), 500

@auth_bp.route("/logout", methods=["POST"])
@login_required()
def logout(user_id):
    """
    Realiza logout invalidando o token atual (blacklist).
    """
    try:
        token = get_token_from_header()
        if token:
            add_to_blacklist(token)
            logger.info(f"Logout realizado para user_id={user_id}")
        return jsonify({"status": "success", "message": "Logout realizado com sucesso"}), 200

    except Exception as e:
        logger.error(f"Erro interno no logout: {str(e)}")
        return jsonify({"status": "error", "message": "Erro interno no servidor"}), 500

@auth_bp.route("/me", methods=["GET"])
@login_required(inject_user=True)
def me(user_id, user):
    """
    Retorna dados do usuário autenticado.
    """
    try:
        return jsonify({"status": "success", "data": user.to_dict()}), 200
    except Exception as e:
        logger.error(f"Erro ao obter dados do usuário {user_id}: {str(e)}")
        return jsonify({"status": "error", "message": "Erro ao buscar informações do usuário"}), 500
