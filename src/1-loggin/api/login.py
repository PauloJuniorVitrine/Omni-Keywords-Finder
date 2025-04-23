# src/1-auth/api/login.py

from flask import Blueprint, request, jsonify, redirect, url_for
from datetime import datetime
from ..utils.jwt_helper import generate_jwt
from ..models.user import UserModel
import re
import logging

auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    # Validação básica de campos
    if not data or "email" not in data or "senha" not in data:
        return jsonify({"erro": "Email e senha são obrigatórios."}), 400

    email = data["email"].strip()
    senha = data["senha"]

    # Validação de formato e tamanho
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return jsonify({"erro": "Formato de e-mail inválido."}), 400

    if len(email) > 150 or len(senha) > 100:
        return jsonify({"erro": "Campos excedem o tamanho permitido."}), 400

    # Busca de usuário no banco
    user = UserModel.find_by_email(email)

    if not user or not user.verify_password(senha):
        logger.warning(f"[Login] Credenciais inválidas para: {email}")
        return jsonify({"erro": "Credenciais inválidas."}), 401

    # Geração do token JWT
    token = generate_jwt(user_id=user.id, email=user.email)

    # Log de sucesso
    logger.info(f"[Login] Autenticação bem-sucedida: {email} em {datetime.utcnow().isoformat()}")

    # Resposta
    return jsonify({
        "mensagem": "Login realizado com sucesso.",
        "token": token,
        "redirect": url_for("theme_manager.view_temas")
    }), 200
