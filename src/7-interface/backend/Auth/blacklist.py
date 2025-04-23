import logging
from typing import Set

logger = logging.getLogger(__name__)

# Armazena os tokens revogados (em memória)
_blacklisted_tokens: Set[str] = set()

def add_to_blacklist(token: str) -> None:
    """
    Adiciona um token à blacklist.

    :param token: Token JWT a ser invalidado
    """
    _blacklisted_tokens.add(token)
    logger.info(f"Token adicionado à blacklist: {token}")

def is_blacklisted(token: str) -> bool:
    """
    Verifica se um token está na blacklist.

    :param token: Token JWT recebido
    :return: True se o token estiver revogado
    """
    resultado = token in _blacklisted_tokens
    if resultado:
        logger.info(f"Token bloqueado detectado: {token}")
    return resultado

def clear_blacklist() -> None:
    """
    Limpa todos os tokens da blacklist (uso interno para testes).
    """
    _blacklisted_tokens.clear()
    logger.warning("Blacklist limpa manualmente.")

def get_all_blacklisted() -> Set[str]:
    """
    Retorna todos os tokens atualmente bloqueados.

    :return: Conjunto de tokens bloqueados
    """
    return _blacklisted_tokens.copy()

def initialize_blacklist(tokens: Set[str]) -> None:
    """
    Inicializa a blacklist com um conjunto de tokens (útil para testes ou carregamento externo).

    :param tokens: Tokens a serem adicionados à blacklist
    """
    _blacklisted_tokens.update(tokens)
    logger.info(f"Blacklist inicializada com {len(tokens)} tokens.")
