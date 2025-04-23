# src/1-auth/utils/jwt_helper.py

import jwt
from datetime import datetime, timedelta
from flask import current_app

def generate_jwt(user_id: int, email: str, expires_in: int = 120):
    """
    Gera um token JWT válido por X minutos.
    """
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.utcnow() + timedelta(minutes=expires_in),
        "iat": datetime.utcnow()
    }

    secret = current_app.config.get("JWT_SECRET", "default-secret")
    algorithm = current_app.config.get("JWT_ALGORITHM", "HS256")

    token = jwt.encode(payload, secret, algorithm=algorithm)
    return token

def verify_jwt(token: str):
    """
    Verifica e decodifica um token JWT.
    Retorna o payload se válido, ou None se inválido/expirado.
    """
    try:
        secret = current_app.config.get("JWT_SECRET", "default-secret")
        algorithm = current_app.config.get("JWT_ALGORITHM", "HS256")
        payload = jwt.decode(token, secret, algorithms=[algorithm])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
