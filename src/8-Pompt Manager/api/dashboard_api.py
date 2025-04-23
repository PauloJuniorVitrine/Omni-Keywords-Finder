import os
import json
import logging
import redis
import asyncio
import bcrypt
import psutil
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends, WebSocket
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel
from typing import List
import graphene
from starlette.graphql import GraphQLApp

# 🔹 Carregar variáveis de ambiente
load_dotenv()

# 🔹 Configuração de Logs Estruturados
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("dashboard_api.log"), logging.StreamHandler()]
)

# 🔹 Configuração do FastAPI
app = FastAPI()

# 🔹 Configuração do Redis para Cache
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=4, decode_responses=True)

# 🔹 Configuração do Banco de Dados Assíncrono
DATABASE_URL = "sqlite+aiosqlite:///database/system_data.db"
engine = create_async_engine(DATABASE_URL, echo=True, future=True)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

def get_db_session():
    """Gera uma sessão assíncrona do banco de dados."""
    return async_session()

# 🔹 Autenticação JWT
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

async def generate_token(user_id: str):
    """Gera um token JWT válido por 60 minutos."""
    payload = {
        "sub": user_id,
        "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

async def verify_token(token: str = Depends(oauth2_scheme)):
    """Verifica e decodifica um token JWT."""
    try:
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return decoded_token["sub"]
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")

# 🔹 Modelos Pydantic
class Nicho(BaseModel):
    nome: str
    palavras_permitidas: List[str]

# 🔹 Worker para Atualizar Cache Periodicamente
async def atualizar_cache():
    while True:
        async with async_session() as session:
            result = await session.execute("SELECT nome, palavras_permitidas FROM nichos")
            nichos = [{"nome": row["nome"], "palavras_permitidas": json.loads(row["palavras_permitidas"])} for row in result]
            redis_client.setex("nichos", 600, json.dumps(nichos))
        await asyncio.sleep(600)
asyncio.create_task(atualizar_cache())

# 🔹 GraphQL Schema
class Query(graphene.ObjectType):
    hello = graphene.String(default_value="Bem-vindo ao GraphQL Dashboard API")
app.add_route("/graphql", GraphQLApp(schema=graphene.Schema(query=Query)))

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Autenticação com geração de token JWT."""
    senha_armazenada = bcrypt.hashpw("password".encode('utf-8'), bcrypt.gensalt())
    if not bcrypt.checkpw(form_data.password.encode('utf-8'), senha_armazenada):
        raise HTTPException(status_code=400, detail="Credenciais inválidas")
    token = await generate_token(form_data.username)
    return {"access_token": token, "token_type": "bearer"}

@app.get("/metrics")
async def get_metrics():
    """Retorna métricas detalhadas da API."""
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "cpu_usage": psutil.cpu_percent(interval=1),
        "memory_usage": psutil.virtual_memory().percent,
        "requests_handled": redis_client.get("requests_count") or 0
    }

# 🔹 WebSocket para Atualizações em Tempo Real
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        stats = redis_client.get("nichos")
        if stats:
            await websocket.send_text(stats)
        await asyncio.sleep(10)

if __name__ == "__main__":
    logging.info("🚀 API Dashboard iniciada com sucesso!")
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
