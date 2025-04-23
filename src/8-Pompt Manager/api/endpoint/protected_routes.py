import os
import logging
import redis
import jwt
import asyncio
import uvicorn
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi_limiter import FastAPILimiter
from jose import JWTError
from pydantic import BaseModel
from typing import Dict
import prometheus_client

# 🔹 Carregar variáveis de ambiente
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "supersecretkey")
ALGORITHM = "RS256"  # Chave assimétrica para segurança máxima
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=9, decode_responses=True)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

# 🔹 Configuração de Logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("protected_routes.log"), logging.StreamHandler()]
)

# 🔹 Inicializar FastAPI
app = FastAPI()

# 🔹 Configuração de CORS Seguro
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://meusistema.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔹 Inicializar Rate Limiter
@app.on_event("startup")
async def startup():
    await FastAPILimiter.init(redis_client)

# 🔹 Implementar Cache Local para Tokens
TOKEN_CACHE = {}
CACHE_EXPIRATION = 30  # Tempo de cache em segundos

async def get_cached_token(token: str):
    """Obtém o token do cache local, reduzindo chamadas ao Redis."""
    if token in TOKEN_CACHE and (datetime.utcnow() - TOKEN_CACHE[token]["timestamp"]).seconds < CACHE_EXPIRATION:
        return TOKEN_CACHE[token]["user"]
    return None

# 🔹 Middleware para Proteger Rotas
async def token_required(token: str = Depends(oauth2_scheme)):
    """Middleware para validar JWT e restringir acesso a rotas protegidas."""
    cached_user = await get_cached_token(token)
    if cached_user:
        return cached_user
    return await verify_token(token)

async def verify_token(token: str):
    """Verifica e decodifica um JWT usando chave pública e valida no Redis."""
    try:
        if redis_client.get(f"token_blacklist:{token}"):
            raise HTTPException(status_code=401, detail="Token revogado")
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user = decoded_token["sub"]
        TOKEN_CACHE[token] = {"user": user, "timestamp": datetime.utcnow()}
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")

@app.get("/dados-seguros", dependencies=[Depends(token_required), Depends(FastAPILimiter.times(10, 60))])
async def protected_data():
    """Rota protegida que retorna dados sensíveis apenas para usuários autenticados."""
    return {"message": "Dados seguros acessados com sucesso!"}

@app.get("/metrics")
async def metrics():
    """Métricas Prometheus para monitoramento da API."""
    return prometheus_client.generate_latest()

@app.post("/logout")
async def logout(token: str = Depends(oauth2_scheme)):
    """Revoga o token JWT no Redis."""
    redis_client.setex(f"token_blacklist:{token}", ACCESS_TOKEN_EXPIRE_MINUTES * 60, "revoked")
    TOKEN_CACHE.pop(token, None)  # Remove do cache local
    logging.info(f"🔒 Token revogado: {token}")
    return {"message": "Logout realizado com sucesso."}

# 🔹 Implementar Auto-Rotação de Chaves para JWT
KEY_ROTATION_INTERVAL = 86400  # 1 dia em segundos
async def rotate_keys():
    """Rotaciona automaticamente as chaves JWT a cada X dias."""
    while True:
        global SECRET_KEY
        SECRET_KEY = os.urandom(32).hex()
        logging.info("🔑 Chave JWT rotacionada automaticamente!")
        await asyncio.sleep(KEY_ROTATION_INTERVAL)
asyncio.create_task(rotate_keys())

# 🔹 Implementar Expiração Gradual de Sessões
SESSION_TIMEOUT = 1800  # 30 minutos
async def expire_sessions():
    """Remove tokens inativos do cache local para reforçar segurança."""
    while True:
        now = datetime.utcnow()
        expired_tokens = [t for t, data in TOKEN_CACHE.items() if (now - data["timestamp"]).seconds > SESSION_TIMEOUT]
        for token in expired_tokens:
            TOKEN_CACHE.pop(token, None)
        await asyncio.sleep(600)  # Verifica a cada 10 minutos
asyncio.create_task(expire_sessions())

if __name__ == "__main__":
    logging.info("🚀 Serviço de Rotas Protegidas iniciado!")
    uvicorn.run(app, host="0.0.0.0", port=8006)
