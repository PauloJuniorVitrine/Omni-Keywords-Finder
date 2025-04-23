import json
import os
from typing import Optional
from datetime import datetime
from cryptography.fernet import Fernet, InvalidToken

# =============================
# CONFIGURAÇÕES
# =============================
CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_DB", "credentials/google_ads_token.json")
ENCRYPTION_KEY = os.getenv("GOOGLE_TOKEN_KEY")  # Use Fernet.generate_key()

def _get_fernet() -> Optional[Fernet]:
    if ENCRYPTION_KEY:
        return Fernet(ENCRYPTION_KEY.encode())
    return None

# =============================
# SALVAR TOKEN
# =============================
def salvar_token(token_data: dict, perfil: str = "default") -> None:
    token_data = token_data.copy()
    token_data['saved_at'] = datetime.utcnow().isoformat()

    os.makedirs(os.path.dirname(CREDENTIALS_FILE), exist_ok=True)
    filename = _get_token_path(perfil)
    data = json.dumps(token_data, ensure_ascii=False, indent=2)

    fernet = _get_fernet()
    if fernet:
        data = fernet.encrypt(data.encode()).decode()

    with open(filename, "w", encoding="utf-8") as f:
        f.write(data)

# =============================
# CARREGAR TOKEN
# =============================
def carregar_token(perfil: str = "default") -> Optional[dict]:
    filename = _get_token_path(perfil)
    if not os.path.exists(filename):
        return None

    with open(filename, "r", encoding="utf-8") as f:
        data = f.read()

    fernet = _get_fernet()
    if fernet:
        try:
            data = fernet.decrypt(data.encode()).decode()
        except InvalidToken:
            raise ValueError("Falha ao descriptografar token: chave incorreta ou conteúdo corrompido.")

    token = json.loads(data)
    if not _validar_token(token):
        raise ValueError("Token carregado está incompleto ou inválido.")

    return token

# =============================
# DELETAR TOKEN
# =============================
def deletar_token(perfil: str = "default") -> None:
    filename = _get_token_path(perfil)
    if os.path.exists(filename):
        os.remove(filename)

# =============================
# AJUDARES INTERNOS
# =============================
def _get_token_path(perfil: str) -> str:
    if perfil == "default":
        return CREDENTIALS_FILE
    return CREDENTIALS_FILE.replace(".json", f"_{perfil}.json")

def _validar_token(token: dict) -> bool:
    campos = ["token", "refresh_token", "token_uri", "client_id", "client_secret", "scopes"]
    return all(k in token for k in campos)

# =============================
# EXEMPLO DE USO (DEV)
# =============================
if __name__ == "__main__":
    token_mock = {
        "token": "ya29.a0AW....",
        "refresh_token": "1//0g...",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "abc.apps.googleusercontent.com",
        "client_secret": "xyz",
        "scopes": ["https://www.googleapis.com/auth/adwords"]
    }
    salvar_token(token_mock, perfil="afds")
    print("Token carregado:", carregar_token("afds"))
    deletar_token("afds")
