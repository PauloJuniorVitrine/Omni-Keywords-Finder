from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from prompt_manager.templates_editor.routes import router as templates_router
from prompt_manager.templates_editor.dashboard_views import router as dashboard_router

app = FastAPI(
    title="Omni Prompt Manager",
    description="Gerenciador de Templates, Métricas e Execução de Prompts",
    version="1.0.0"
)

# 🔐 Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 📋 Middleware de Logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"📥 {request.method} {request.url}")
    response = await call_next(request)
    print(f"📤 {response.status_code}")
    return response

# 🔌 Endpoints de sistema
@app.get("/ping", tags=["Infra"])
def ping():
    return {"status": "ok"}

# 📁 Arquivos estáticos (CSS, JS, etc.)
app.mount("/static", StaticFiles(directory="static"), name="static")

# 🔗 Registro de módulos
app.include_router(templates_router, prefix="/admin/templates", tags=["Templates"])
app.include_router(dashboard_router, tags=["Dashboard"])
