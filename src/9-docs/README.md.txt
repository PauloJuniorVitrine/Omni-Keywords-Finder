# 🔍 Omni Keywords Finder

Sistema modular e automatizado para descoberta, validação e empacotamento de palavras-chave de alto potencial para blogs, redes sociais e produtos digitais. Desenvolvido com foco em escalabilidade, orquestração inteligente e alto desempenho em tarefas de SEO e marketing de conteúdo.

---

## 🚀 Funcionalidades Principais

- Autenticação segura com JWT
- Gerenciamento de nichos, temas e categorias
- Coleta automatizada de palavras-chave (Google, YouTube, Reddit etc.)
- Validação via Google Ads Planner + Score por relevância
- Geração de prompts otimizados com placeholders
- Exportação automática para publicação e agendamento
- Interface web com dashboard interativo
- Sistema agendador com cronjobs
- APIs RESTful para integração com serviços externos

---

## 🏗️ Arquitetura do Sistema

O projeto está dividido em 13 módulos independentes e coesos:

1-loggin/ → Autenticação e proteção de rotas 2-Theme Manager/ → Gestão de temas, nichos e categorias 3-data base/ → Banco de dados, ORM e pipelines 4-colector/ → Coleta de palavras em múltiplas fontes 5-keyword validation/ → Filtros, scoring e validação com Google Planner 6-api/ → Integração com redes e endpoints externos 7-interface/ → Interface Web (Frontend React + Backend Flask) 8-Pompt Manager/ → Recebimento, templates, zipagem e entrega de prompts 9-docs/ → Documentação técnica e instruções 10-config/ → Gerenciamento de configuração e ambientes 11-Integrator/ → Integração orquestrada entre módulos 12-keywords/ → Variações, registros e estatísticas de uso 13-auth/ → Autorização com Google OAuth2 (ex: Planner API)


---

## 🛠️ Tecnologias Utilizadas

- **Python 3.11+**
- **Flask**, **APScheduler**, **SQLAlchemy**
- **React.js**, **JSX**, **Tailwind CSS**
- **PostgreSQL / SQLite**
- **JWT Auth**, **OAuth2**, **Google API**
- **PyTest** para testes automatizados
- **dotenv**, **pydantic**, **jsonschema**

---

## 📦 Instalação Local

### Pré-requisitos

```bash
Python 3.11+
Node.js 18+
PostgreSQL ou SQLite

Clonar o projeto

git clone https://github.com/seu-usuario/omni-keywords-finder.git
cd omni-keywords-finder

Criar ambiente virtual

python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

Instalar dependências

pip install -r requirements.txt

🔐 Variáveis de Ambiente

Configurar arquivos .env na pasta /10-config/:

.env.development.txt

ENV=development
DATABASE_URL=sqlite:///system_data.db
SECRET_KEY=sua_chave_secreta
GOOGLE_API_KEY=sua_api_google

.env.production.txt
ENV=production
DATABASE_URL=postgresql://user:pass@localhost:5432/omni


▶️ Como Executar o Sistema
Backend (Flask)

Frontend (React)

cd src/7-interface/frontend
npm install
npm run dev

🔁 Fluxo de Execução

    Usuário faz login e escolhe tema

    Sistema coleta palavras dos canais ativados

    Palavras são validadas via Google Planner

    Palavras com melhor score são enviadas ao Prompt Manager

    Geração automática dos prompts (placeholders dinâmicos)

    Pacote final exportado (ZIP) e pronto para publicação

    📁 Estrutura de Pastas (Resumida)

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
└── ...
🧪 Testes

Rodar todos os testes unitários:



pytest


Localização dos testes:

    /1-loggin/tests

    /2-Theme Manager/tests

    /3-data base/tests db

    /4-colector/tests colector

    /5-keyword validation/tests keywords validation

    /6-api/tests api

🗺️ Roadmap Futuro

Melhorar camada de cache com Redis

Implementar versionamento de prompts

Dashboard com estatísticas de desempenho (via Grafana)

    Integração com Notion API e Google Drive

🤝 Contribuições

Pull Requests são bem-vindos. Para grandes mudanças, por favor, abra uma issue primeiro para discutir o que deseja modificar.
📄 Licença

Este projeto é privado. Direitos autorais reservados ao autor.


---

Se quiser, posso salvar este README direto no módulo `9-docs` com o nome `README.md`. Deseja que eu faça isso? E deseja incluir nome de autor, link de repositório ou licença específica (MIT, GPL, etc)?



