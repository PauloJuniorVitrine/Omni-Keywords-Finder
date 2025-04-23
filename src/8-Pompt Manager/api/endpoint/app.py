from flask import Flask
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging

from config.settings import SECRET_KEY, RATE_LIMITS
from endpoints.auth import auth_bp
from endpoints.protected_routes import protected_bp

# Configuração do Flask
app = Flask(__name__)
CORS(app)  # Habilita CORS para permitir requisições externas

# Configuração de Rate Limiting
limiter = Limiter(get_remote_address, app=app, default_limits=RATE_LIMITS)

# Registrar Blueprints
app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(protected_bp, url_prefix="/protected")

# Configuração de logging global
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

@app.route("/")
def home():
    return {"mensagem": "API Omni Keywords Finder está ativa!"}

if __name__ == "__main__":
    app.run(debug=True)
