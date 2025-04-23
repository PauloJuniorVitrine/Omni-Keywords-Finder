import logging
from functools import wraps
from flask import request, jsonify
from .utils import decode_token, get_token_from_header
from .blacklist import is_blacklisted

logger = logging.getLogger(__name__)

def login_required(inject_user: bool = False):
    """
    Decorador que protege rotas com autenticação JWT.
    Injeta o user_id por padrão e opcionalmente o objeto User.

    :param inject_user: Se True, injeta o objeto User no endpoint
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            token = get_token_from_header()

            if not token:
                logger.warning("Token não fornecido")
                return jsonify({'error': 'Token não fornecido'}), 401

            if is_blacklisted(token):
                logger.warning("Token revogado detectado")
                return jsonify({'error': 'Token revogado (logout)'}), 401

            user_id = decode_token(token)
            if not user_id:
                logger.warning("Token inválido ou expirado")
                return jsonify({'error': 'Token inválido ou expirado'}), 401

            if inject_user:
                from src.3_data_base.database_connection import Session
                from src.7_interface.backend.models.user import User
                session = Session()
                user = session.query(User).get(user_id)
                if not user:
                    logger.warning(f"Usuário {user_id} não encontrado no banco")
                    return jsonify({'error': 'Usuário não encontrado'}), 404
                return f(user_id=user_id, user=user, *args, **kwargs)

            return f(user_id=user_id, *args, **kwargs)
        return decorated
    return decorator

def role_required(required_role: str):
    """
    Decorador para rotas que exigem um perfil específico.

    :param required_role: Papel necessário (ex: 'admin')
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            token = get_token_from_header()

            if not token:
                logger.warning("Token não fornecido")
                return jsonify({'error': 'Token não fornecido'}), 401

            if is_blacklisted(token):
                logger.warning("Token revogado detectado")
                return jsonify({'error': 'Token revogado'}), 401

            user_id = decode_token(token)
            if not user_id:
                logger.warning("Token inválido ou expirado")
                return jsonify({'error': 'Token inválido ou expirado'}), 401

            from src.3_data_base.database_connection import Session
            from src.7_interface.backend.models.user import User
            session = Session()
            user = session.query(User).get(user_id)

            if not user:
                logger.warning(f"Usuário {user_id} não encontrado")
                return jsonify({'error': 'Usuário não encontrado'}), 404

            if user.role != required_role:
                logger.warning(f"Acesso negado: usuário {user.email} não é {required_role}")
                return jsonify({'error': 'Acesso não autorizado'}), 403

            return f(user_id=user.id, user=user, *args, **kwargs)
        return decorated
    return decorator
