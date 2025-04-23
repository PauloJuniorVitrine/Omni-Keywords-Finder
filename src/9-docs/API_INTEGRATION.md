# 🔗 Integração com a API — Omni Keywords Finder

Este documento descreve como **outros sistemas** podem se conectar à API do Omni Keywords Finder para **autenticar, requisitar prompts e baixar pacotes ZIP** com os conteúdos gerados.

## 🔐 1. Autenticação via JWT

### `POST /login`
```http
POST http://localhost:5000/login
```

**Body:**
```json
{
  "username": "admin",
  "password": "senha123"
}
```

**Response:**
```json
{
  "access_token": "JWT_TOKEN",
  "token_type": "bearer"
}
```

Use o token JWT nos próximos requests com:

```
Authorization: Bearer JWT_TOKEN
```

## 📦 2. Obter ZIP com prompts

### `GET /exportar/zip`

**Requisição:**
```http
GET http://localhost:5000/exportar/zip
Authorization: Bearer JWT_TOKEN
```

**Resposta:** arquivo `.zip` com estrutura como:
```
/exportado.zip
├── nicho_marketing/
│   ├── prompts_instagram.txt
│   ├── prompts_youtube.txt
```

## 🧠 Endpoints úteis
- `GET /temas`
- `GET /config`
- `GET /health`

## 🧰 Requisitos Técnicos
- JWT obrigatório
- JSON e ZIP suportados
- Charset UTF-8

## 💡 Exemplo Python

```python
import requests

res = requests.post("http://localhost:5000/login", json={
    "username": "admin",
    "password": "senha123"
})
token = res.json()["access_token"]

res = requests.get("http://localhost:5000/exportar/zip", headers={
    "Authorization": f"Bearer {token}"
})
with open("prompts.zip", "wb") as f:
    f.write(res.content)
```
