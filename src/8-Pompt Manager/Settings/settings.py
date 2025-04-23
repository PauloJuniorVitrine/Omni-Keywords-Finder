import os
import secrets
from dotenv import load_dotenv
import logging

# 🔄 Carregar variáveis do arquivo .env
load_dotenv()

# 🔐 Segurança
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))
DEBUG = os.getenv("DEBUG", "False") == "True"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ⚡ Rate Limits (configurável via ambiente)
RATE_LIMITS = os.getenv("RATE_LIMITS", "100 per minute")

# 📦 Configuração de Banco de Dados
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///db.sqlite3")

# 🌐 Configuração de CORS
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "True") == "True"

# 📊 Cache (configurável via Redis ou Memcached)
CACHE_TYPE = os.getenv("CACHE_TYPE", "simple")  # simple, redis, memcached
CACHE_DEFAULT_TIMEOUT = int(os.getenv("CACHE_DEFAULT_TIMEOUT", 300))

# 🔄 Configuração de Auto Reload
AUTO_RELOAD = os.getenv("AUTO_RELOAD", "True") == "True"

# 🔐 Segurança Avançada
JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", 3600))  # Expira em 1 hora
SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer-when-downgrade",
}

# 📢 Configuração de Logs
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(levelname)s - %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": "logs/app.log",
            "formatter": "default",
        },
    },
    "root": {
        "level": LOG_LEVEL,
        "handlers": ["console", "file"],
    },
}

# 🚀 Módulos de Configuração Modular
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
if ENVIRONMENT == "development":
    from settings.development import *
elif ENVIRONMENT == "production":
    from settings.production import *
