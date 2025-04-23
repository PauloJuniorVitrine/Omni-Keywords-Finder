# send_to_api.py (versão assíncrona + robusta + melhorias finais)

import os
import json
import time
import uuid
import hmac
import hashlib
import logging
import aiohttp
import asyncio
from typing import Dict, Optional
from datetime import datetime

from tenacity import retry, stop_after_attempt, wait_exponential

from api_config import redis_cache, ENVIAR_RESULTADOS, SECRET_KEY

logger = logging.getLogger("SEND_API")
logging.basicConfig(level=logging.INFO)

# ------------------------
# Função utilitária para logs
# ------------------------
def log_com_trace(msg: str, trace_id: Optional[str] = None, level: str = "info"):
    prefix = f"[{trace_id}]" if trace_id else "[no-trace]"
    full_msg = f"{prefix} {msg}"
    getattr(logger, level)(full_msg)

# ------------------------
# Função para assinar payload
# ------------------------
def assinar_payload(payload: dict, secret: str) -> str:
    payload_str = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hmac.new(secret.encode(), payload_str, hashlib.sha256).hexdigest()

# ------------------------
# Validação de payload
# ------------------------
def validar_payload(payload: dict, campos_obrigatorios: Optional[list] = None):
    campos_obrigatorios = campos_obrigatorios or ["id", "conteudo", "tipo"]
    for campo in campos_obrigatorios:
        if campo not in payload:
            raise ValueError(f"Payload inválido: campo obrigatório ausente: {campo}")

# ------------------------
# Envio com retry
# ------------------------
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def _enviar(destino: str, payload: dict, headers: dict, trace: str):
    async with aiohttp.ClientSession() as session:
        async with session.post(destino, json=payload, headers=headers, timeout=15) as resposta:
            duracao = time.time()
            if resposta.status == 200:
                log_com_trace("Envio concluído com sucesso", trace)
                return {"status": "sucesso", "trace_id": trace, "duracao": duracao}
            else:
                texto = await resposta.text()
                log_com_trace(f"Falha no envio: status {resposta.status} - {texto}", trace, level="error")
                raise Exception(f"Erro HTTP {resposta.status}: {texto}")

# ------------------------
# Função principal de envio assíncrono
# ------------------------
async def send_payload(
    destino: str,
    payload: Dict,
    headers: Optional[Dict] = None,
    modo_teste: bool = False,
    dry_run: bool = False,
    trace_id: Optional[str] = None,
    salvar_fallback: bool = True
) -> Dict:
    trace = trace_id or f"TRACE-{uuid.uuid4()}"
    log_com_trace(f"Iniciando envio para {destino}", trace)

    if os.getenv("FORCAR_ERRO") == "1":
        raise RuntimeError("Simulação de falha forçada para teste")

    if not ENVIAR_RESULTADOS and not modo_teste:
        log_com_trace("Envio desabilitado por configuração (ENVIAR_RESULTADOS=False)", trace, level="warning")
        return {"status": "aborted", "reason": "Envio desabilitado", "trace_id": trace}

    if dry_run:
        log_com_trace("Modo dry-run ativado. Nenhum dado será enviado.", trace, level="warning")
        return {"status": "dry-run", "trace_id": trace}

    try:
        validar_payload(payload)

        payload_assinado = payload.copy()
        payload_assinado["assinatura"] = assinar_payload(payload, SECRET_KEY)
        payload_assinado["trace_id"] = trace

        headers = headers or {"Content-Type": "application/json"}
        inicio = time.time()
        resultado = await _enviar(destino, payload_assinado, headers, trace)
        resultado["duracao"] = time.time() - inicio
        return resultado

    except Exception as e:
        log_com_trace(f"Erro no envio: {e}", trace, level="error")

        if salvar_fallback:
            chave_fallback = f"fallback:{trace}:{datetime.now().isoformat()}"
            try:
                redis_cache.setex(chave_fallback, 86400, json.dumps(payload))
                log_com_trace(f"Payload salvo no fallback Redis: {chave_fallback}", trace)
            except Exception as redis_err:
                log_com_trace(f"Falha ao salvar no Redis: {redis_err}", trace,