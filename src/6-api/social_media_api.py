# social_media_api.py (versão Enterprise Absoluto com logging estendido, webhook, healthcheck e banco futuro)

import os
import json
import aiohttp
import asyncio
import logging
import requests
from datetime import datetime
from typing import Optional, Dict, List
from tenacity import retry, stop_after_attempt, wait_exponential
from prometheus_client import Counter

from api_config import redis_cache
from send_to_api import assinar_payload, log_com_trace

logger = logging.getLogger("SOCIAL_MEDIA")

# ------------------------
# Métricas Prometheus
# ------------------------
ENVIO_SUCESSO = Counter("social_envio_sucesso_total", "Total de envios com sucesso", ["canal"])
ENVIO_FALHA = Counter("social_envio_falha_total", "Total de falhas de envio", ["canal"])

# ------------------------
# Validação de parâmetros
# ------------------------
def validar_dados_social(dados: Dict):
    obrigatorios = ["canal", "tema", "conteudo"]
    for campo in obrigatorios:
        if campo not in dados or not dados[campo]:
            raise ValueError(f"Campo obrigatório ausente: {campo}")

    conteudo = dados.get("conteudo", "")
    if len(conteudo) < 20 or "http" in conteudo:
        raise ValueError("Conteúdo inválido: muito curto ou contém URLs")

# ------------------------
# Envio com retry (1 canal)
# ------------------------
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def _enviar_conteudo(canal: str, payload: Dict, headers: Dict, trace_id: str):
    url_destino = os.getenv(f"URL_SOCIAL_{canal.upper()}")
    if not url_destino:
        raise ValueError(f"Canal '{canal}' não configurado")

    inicio = datetime.utcnow()
    async with aiohttp.ClientSession() as session:
        async with session.post(url_destino, json=payload, headers=headers, timeout=10) as resp:
            duracao = (datetime.utcnow() - inicio).total_seconds()
            tamanho = len(json.dumps(payload))

            if resp.status == 200:
                log_com_trace(f"[{canal}] Sucesso - {duracao:.2f}s, {tamanho}B", trace_id)
                ENVIO_SUCESSO.labels(canal=canal).inc()
                return {
                    "status": "sucesso",
                    "canal": canal,
                    "trace_id": trace_id,
                    "tempo_execucao": duracao,
                    "tamanho_payload": tamanho
                }
            else:
                erro = await resp.text()
                log_com_trace(f"[{canal}] Falha {resp.status}: {erro}", trace_id, level="error")
                ENVIO_FALHA.labels(canal=canal).inc()
                raise Exception(f"Erro HTTP {resp.status}: {erro}")

# ------------------------
# Envio em paralelo para múltiplos canais (futuro)
# ------------------------
async def enviar_em_lote(lista_dados: List[Dict], **kwargs):
    tarefas = [enviar_para_rede_social(d, **kwargs) for d in lista_dados]
    return await asyncio.gather(*tarefas, return_exceptions=True)

# ------------------------
# Healthcheck de conectividade
# ------------------------
async def testar_conectividade():
    canais = ["linkedin", "instagram", "twitter"]
    results = {}
    async with aiohttp.ClientSession() as session:
        for canal in canais:
            url = os.getenv(f"URL_SOCIAL_{canal.upper()}")
            if not url:
                results[canal] = "não configurado"
                continue
            try:
                async with session.head(url, timeout=5) as resp:
                    results[canal] = f"{resp.status}"
            except Exception as e:
                results[canal] = f"erro: {str(e)}"
    return results

# ------------------------
# Envio principal
# ------------------------
async def enviar_para_rede_social(
    dados: Dict,
    modo_teste: bool = False,
    dry_run: bool = False,
    trace_id: Optional[str] = None,
    salvar_fallback: bool = True
) -> Dict:
    trace = trace_id or f"TRACE-{os.urandom(8).hex()}"
    log_com_trace("Iniciando envio para rede social", trace)

    if os.getenv("FORCAR_ERRO_SOCIAL") == "1":
        raise RuntimeError("Erro forçado para teste de fallback")

    try:
        validar_dados_social(dados)

        canal = dados["canal"]
        headers = {"Content-Type": "application/json"}

        payload = dados.copy()
        payload["assinatura"] = assinar_payload(dados, os.getenv("SECRET_KEY", "default"))
        payload["trace_id"] = trace

        if dry_run:
            log_com_trace("[dry-run] Payload pronto, mas não enviado", trace, level="warning")
            return {"status": "dry-run", "trace_id": trace, "canal": canal}

        resultado = await _enviar_conteudo(canal, payload, headers, trace)
        # Simulação de persistência futura
        # registrar_envio_em_db(resultado)
        return resultado

    except Exception as e:
        log_com_trace(f"Erro ao enviar conteúdo: {e}", trace, level="error")
        ENVIO_FALHA.labels(canal=dados.get("canal", "indefinido")).inc()

        if salvar_fallback:
            chave_fallback = f"social:{trace}:{datetime.now().isoformat()}"
            try:
                redis_cache.setex(chave_fallback, 86400, json.dumps(dados))
                log_com_trace(f"Conteúdo salvo no fallback Redis: {chave_fallback}", trace)
            except Exception as err:
                log_com_trace(f"Erro salvando no Redis: {err}", trace, level="error")

        webhook = os.getenv("WEBHOOK_ALERTA")
        if webhook:
            try:
                requests.post(webhook, json={"trace_id": trace, "erro": str(e)}, timeout=5)
                log_com_trace("Webhook de falha notificado", trace)
            except Exception as werr:
                log_com_trace(f"Erro no webhook: {werr}", trace, level="warning")

        return {"status": "falha", "erro": str(e), "trace_id": trace}
