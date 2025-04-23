import os
import logging
import redis
import jwt
import asyncio
import uvicorn
import psycopg2
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi_limiter import FastAPILimiter
from jose import JWTError
from pydantic import BaseModel
from typing import Dict
import pyotp
import smtplib
from email.message import EmailMessage

# 🔹 Carregar variáveis de ambiente
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
DB_URL = os.getenv("DATABASE_URL", "dbname=auth_db user=admin password=admin host=localhost port=5432")

redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=8, decode_responses=True)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

# 🔹 Configuração de Logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("auth.log"), logging.StreamHandler()]
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

# 🔹 Conectar ao Banco de Dados
def get_db_connection():
    return psycopg2.connect(DB_URL)

# 🔹 Modelo Pydantic para Requisição
class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str

# 🔹 Banco de Usuários e Sessões Ativas
TOTP_SECRETS = {}

async def generate_token(user_id: str, is_refresh=False):
    """Gera um JWT válido e armazena no Redis e Banco de Dados."""
    expire = datetime.utcnow() + (timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS) if is_refresh else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {"sub": user_id, "exp": expire, "is_refresh": is_refresh}
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    redis_client.setex(f"token:{token}", REFRESH_TOKEN_EXPIRE_DAYS * 86400 if is_refresh else ACCESS_TOKEN_EXPIRE_MINUTES * 60, "valid")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO active_tokens (user_id, token, is_refresh) VALUES (%s, %s, %s)", (user_id, token, is_refresh))
    conn.commit()
    conn.close()
    return token

async def verify_token(token: str):
    """Verifica e decodifica um JWT."""
    try:
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if redis_client.get(f"token:{token}") is None:
            raise HTTPException(status_code=401, detail="Token revogado ou expirado")
        return decoded_token["sub"]
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")

@app.post("/logout")
async def logout(token: str = Depends(oauth2_scheme)):
    """Revoga o token JWT e encerra todas as sessões do usuário."""
    user = await verify_token(token)
    redis_client.delete(f"token:{token}")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM active_tokens WHERE user_id = %s", (user,))
    conn.commit()
    conn.close()
    
    logging.info(f"🔒 Logout global realizado para {user}")
    return {"message": "Logout global realizado com sucesso."}

@app.get("/audit-log")
async def get_audit_log():
    """Retorna os logs de autenticação."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM auth_logs ORDER BY timestamp DESC LIMIT 50")
    logs = cursor.fetchall()
    conn.close()
    return {"logs": logs}

async def auto_logout_inactive_users():
    """Desloga usuários inativos automaticamente."""
    while True:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM active_tokens WHERE last_activity < NOW() - INTERVAL '30 minutes'")
        conn.commit()
        conn.close()
        await asyncio.sleep(1800)  # Verifica a cada 30 minutos
asyncio.create_task(auto_logout_inactive_users())

if __name__ == "__main__":
    logging.info("🚀 Serviço de Autenticação iniciado!")
    uvicorn.run(app, host="0.0.0.0", port=8005)
