import requests
import logging
from typing import List

logger = logging.getLogger("prompt_sender")
logging.basicConfig(level=logging.INFO)

# =============================
# CONFIGURAÇÕES DO PROMPT MANAGER
# =============================
PROMPT_MANAGER_URL = "http://localhost:8000/prompt/receber_palavra"

# =============================
# ENVIO PARA PROMPT MANAGER
# =============================
def enviar_ao_prompt_manager(lista: List[dict], timeout: int = 5):
    enviados = 0
    falhas = 0
    for item in lista:
        try:
            response = requests.post(PROMPT_MANAGER_URL, json=item, timeout=timeout)
            response.raise_for_status()
            logger.info(f"📤 Enviado: {item['palavra_chave']} | trace_id={item['trace_id']}")
            enviados += 1
        except Exception as e:
            logger.error(f"❌ Falha ao enviar '{item['palavra_chave']}': {e}")
            falhas += 1

    logger.info(f"✅ Envio finalizado: {enviados} enviados, {falhas} falhas.")
    return {"enviados": enviados, "falhas": falhas}


# =============================
# EXEMPLO DE USO
# =============================
if __name__ == "__main__":
    exemplos = [
        {
            "palavra_chave": "funil de vendas digital",
            "nicho": "Marketing",
            "categoria": "Domingo",
            "tema": "Conversão",
            "score": 1345.2,
            "trace_id": "demo-1234"
        }
    ]
    enviar_ao_prompt_manager(exemplos)
