import aioredis
import logging
from fastapi import APIRouter, HTTPException
import smtplib
from email.message import EmailMessage

# 🔹 Configuração do Redis Assíncrono
REDIS_HOST = "localhost"
REDIS_PORT = 6379
redis = None
CACHE_BLACKLIST = {}
CACHE_TTL = 30  # Segundos para cache local

async def get_redis():
    global redis
    if redis is None:
        redis = await aioredis.from_url(f"redis://{REDIS_HOST}:{REDIS_PORT}", decode_responses=True)
    return redis

# 🔹 Inicializar Logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("blacklist.log"), logging.StreamHandler()]
)

router = APIRouter()

async def send_alert_email(token: str):
    """Envia um alerta por e-mail quando um token revogado é reutilizado."""
    msg = EmailMessage()
    msg.set_content(f"Tentativa de uso de token revogado detectada! Token: {token}")
    msg["Subject"] = "🔔 ALERTA: Token Revogado em Uso"
    msg["From"] = "security@meusistema.com"
    msg["To"] = "admin@meusistema.com"
    with smtplib.SMTP("localhost") as server:
        server.send_message(msg)
    logging.warning(f"📧 Alerta enviado para admin sobre token revogado: {token}")

async def add_to_blacklist(token: str, expire: int = 3600):
    """Adiciona um token JWT à blacklist e define um tempo de expiração."""
    redis = await get_redis()
    await redis.setex(f"blacklist:{token}", expire, "revoked")
    CACHE_BLACKLIST[token] = expire  # Armazena no cache local
    logging.info(f"🔒 Token revogado: {token}")

async def is_blacklisted(token: str) -> bool:
    """Verifica se um token está na blacklist, usando cache local para melhor performance."""
    if token in CACHE_BLACKLIST:
        return True
    redis = await get_redis()
    exists = await redis.exists(f"blacklist:{token}")
    if exists:
        CACHE_BLACKLIST[token] = CACHE_TTL  # Atualiza cache local
    return exists

async def remove_from_blacklist(token: str):
    """Remove um token da blacklist manualmente."""
    redis = await get_redis()
    await redis.delete(f"blacklist:{token}")
    CACHE_BLACKLIST.pop(token, None)  # Remove do cache local
    logging.info(f"✅ Token removido da blacklist: {token}")

async def list_blacklisted_tokens():
    """Retorna a lista de tokens atualmente na blacklist."""
    redis = await get_redis()
    keys = await redis.keys("blacklist:*")
    return [key.replace("blacklist:", "") for key in keys]

# 🔹 Endpoints de Blacklist
@router.post("/blacklist/add")
async def blacklist_token(token: str):
    await add_to_blacklist(token)
    return {"message": "Token adicionado à blacklist."}

@router.get("/blacklist/check")
async def check_blacklisted(token: str):
    if await is_blacklisted(token):
        await send_alert_email(token)
        raise HTTPException(status_code=401, detail="Token está na blacklist.")
    return {"message": "Token válido."}

@router.delete("/blacklist/remove")
async def remove_blacklisted_token(token: str):
    await remove_from_blacklist(token)
    return {"message": "Token removido da blacklist."}

@router.get("/blacklist/list")
async def get_blacklisted_tokens():
    tokens = await list_blacklisted_tokens()
    return {"blacklisted_tokens": tokens}
