import os
import logging
from flask import Blueprint, redirect, session, request, jsonify, abort
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from auth.credentials_store import salvar_token

# =============================
# CONFIGURAÇÃO E LOGGING
# =============================
logger = logging.getLogger("google_auth")
logging.basicConfig(level=logging.INFO)

auth_bp = Blueprint("auth", __name__)

# =============================
# VARIÁVEIS DE AMBIENTE
# =============================
CLIENT_SECRETS_FILE = os.getenv("GOOGLE_CLIENT_SECRETS", "credentials/client_secret.json")
SCOPES = ["https://www.googleapis.com/auth/adwords"]
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:5000/auth/callback")
GOOGLE_PROFILE = os.getenv("GOOGLE_ACCOUNT_PROFILE", "default")

# =============================
# INÍCIO DO FLUXO OAUTH
# =============================
@auth_bp.route("/auth/google")
def auth_google():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )
    session['oauth_state'] = state
    logger.info("🔐 Redirecionando para login Google...")
    return redirect(auth_url)

# =============================
# CALLBACK DO GOOGLE
# =============================
@auth_bp.route("/auth/callback")
def auth_callback():
    state = session.get("oauth_state")
    if not state:
        logger.warning("⚠️ Estado OAuth ausente na sessão.")
        abort(400, description="Sessão inválida ou expirada.")

    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
        state=state
    )

    flow.fetch_token(authorization_response=request.url)

    credentials = flow.credentials
    token_data = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes
    }

    session['google_ads_token'] = token_data
    salvar_token(token_data, perfil=GOOGLE_PROFILE)
    logger.info(f"✅ Conta Google autenticada e token salvo no perfil '{GOOGLE_PROFILE}'")
    return jsonify({"message": "Conta Google conectada e token salvo com sucesso."})

# =============================
# ROTA DE VERIFICAÇÃO
# =============================
@auth_bp.route("/auth/status")
def auth_status():
    return jsonify({
        "conectado": 'google_ads_token' in session,
        "dados": session.get('google_ads_token', {})
    })
