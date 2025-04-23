import jwt
import logging
from datetime import datetime, timedelta
from typing import Optional
from flask import current_app, request

logger = logging.getLogger(__name__)

def generate_token(user_id: int, expires_in: Optional[int] = None) -> str:
    """
    Gera um token JWT assinado com tempo de expiração.

    :param user_id: ID do usuário autenticado
    :param expires_in: Tempo de expiração em segundos. Se None, usa config padrão.
    :return: Token JWT (str)
    """
    if expires_in is None:
        expires_in = current_app.config.get("JWT_EXPIRATION_SECONDS", 3600)

    payload = {
        'exp': datetime.utcnow() + timedelta(seconds=expires_in),
        'iat': datetime.utcnow(),
        'sub': user_id
    }

    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')

def decode_token(token: str) -> Optional[int]:
    """
    Decodifica um token JWT e retorna o user_id se válido.

    :param token: Token JWT
    :return: ID do usuário (int) ou None se inválido/expirado
    """
    try:
        payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload.get('sub')
    except jwt.ExpiredSignatureError:
        logger.warning("Token expirado")
        return None
    except jwt.InvalidTokenError:
        logger.warning("Token inválido")
        return None

def get_token_from_header() -> Optional[str]:
    """
    Extrai o token JWT do cabeçalho Authorization.

    :return: Token JWT (str) ou None
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.split(" ")[1]
    return None
