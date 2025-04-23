# src/1-auth/utils/auth_required.py

from functools import wraps
from flask import request, jsonify, g
from .jwt_helper import verify_jwt

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization", None)

        if not auth_header:
            return jsonify({"erro": "Token de autenticação ausente."}), 401

        parts = auth_header.split()

        if len(parts) != 2 or parts[0].lower() != "bearer":
            return jsonify({"erro": "Formato de token inválido."}), 401

        token = parts[1]
        payload = verify_jwt(token)

        if not payload:
            return jsonify({"erro": "Token inválido ou expirado."}), 401

        # Torna o payload acessível na requisição
        g.current_user = {
            "user_id": payload.get("sub"),
            "email": payload.get("email")
        }

        return f(*args, **kwargs)
    return decorated_function
