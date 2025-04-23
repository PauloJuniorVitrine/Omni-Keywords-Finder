
# 🔍 Omni Keywords Finder

Sistema modular e automatizado para descoberta, validação e empacotamento de palavras-chave de alto potencial para blogs, redes sociais e produtos digitais.

---

## 📦 Instalação do Sistema

### ✅ Pré-requisitos

- Python 3.11+, Node.js 18+, SQLite/PostgreSQL

### 📁 Clonar o Repositório

```bash
git clone https://github.com/seu-usuario/omni-keywords-finder.git
cd omni-keywords-finder
```

### 🐍 Backend Python

```bash
python -m venv .venv
source .venv/bin/activate  # ou .venv\Scripts\activate
pip install -r requirements.txt
```

### 🌐 Frontend React

```bash
cd src/7-interface/frontend
npm install
```

### 🔐 Variáveis de Ambiente

Copiar `.env.development.txt` para `.env` ou criar `.env.example` com:

```env
DATABASE_URL=sqlite:///system_data.db
GOOGLE_API_KEY=your_google_api_key
SECRET_KEY=your_secret_key
ENV=development
```

### 🗄️ Setup do Banco

```bash
cd src/8-Pompt Manager/database
python setup_database.py
```

### ▶️ Executar

**Backend:**
```bash
cd src/7-interface/backend
python app.py
```

**Frontend:**
```bash
cd src/7-interface/frontend
npm run dev
```

---

## 📡 API — Endpoints REST

### 🔐 POST /login

```json
{
  "username": "usuario",
  "password": "senha"
}
```

### 🎯 GET /temas

Headers: `Authorization: Bearer <jwt_token>`

### 🧲 POST /coletar

```json
{
  "tema_id": 12,
  "nicho_id": 3,
  "canais": ["google", "youtube"]
}
```

### ✅ POST /validar-palavras

```json
{
  "palavras": ["exemplo"],
  "idioma": "pt-BR",
  "regiao": "BR"
}
```

### 🧠 POST /gerar-prompts

```json
{
  "tema_id": 1,
  "template": "como usar {palavra_primaria} em {palavra_secundaria}"
}
```

### 📦 GET /exportar/zip

Retorna um `.zip` com prompts.

### ⚙️ GET /health

```json
{
  "status": "online",
  "versao": "1.2.0",
  "database": "ok"
}
```

---

## 🔧 Testes

```bash
pytest
```

---

## 📁 Estrutura Modular

```
src/
├── 1-loggin/
├── 2-Theme Manager/
├── 3-data base/
├── 4-colector/
├── 5-keyword validation/
├── 6-api/
├── 7-interface/
├── 8-Pompt Manager/
├── 9-docs/
├── 10-config/
├── 11-Integrator/
```

---

## 🗺️ Roadmap

- [ ] Exportação para Notion e WordPress
- [ ] Dashboard com estatísticas
- [ ] Cache com Redis

---

## 🤝 Contribuições

Pull requests são bem-vindos. Para grandes alterações, abra uma issue antes.

---

## 📄 Licença

Este projeto é privado. Todos os direitos reservados.
