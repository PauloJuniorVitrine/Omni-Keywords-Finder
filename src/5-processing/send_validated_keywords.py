# /5-processing/send_validated_keywords.py
import logging
import argparse
import json
import os
import uuid
from datetime import datetime
from time import time
from google_planner_validator import validar_com_google_planner
from prompt_integrator.sender import enviar_ao_prompt_manager
from theme_manager.services.theme_state import get_tema_e_nicho_ativos

# Configurar logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("integrador")

def exportar_log(payload, trace_id, saida="envios"):
    if not os.path.exists(saida):
        os.makedirs(saida)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{saida}/envio_{trace_id}_{timestamp}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    logger.info(f"Log salvo em {path}")

def coletar_contexto():
    logger.info("➡️  Buscando tema e nicho ativos do Theme Manager...")
    contexto = get_tema_e_nicho_ativos()
    tema = contexto.get("tema")
    nicho = contexto.get("nicho")
    if not tema or not nicho:
        logger.error("❌ Tema ou nicho ativos não encontrados.")
        return None, None
    logger.info(f"✅ Tema ativo: {tema} | Nicho ativo: {nicho}")
    return tema, nicho

def montar_payload(validadas, tema, nicho):
    logger.info("📦 Montando payload...")
    payload = []
    required_keys = ["palavra", "score_final", "trace_id", "tipo"]
    for palavra in validadas:
        if palavra["tipo"] in ("primaria", "secundaria") and all(k in palavra and palavra[k] for k in required_keys):
            payload.append({
                "palavra_chave": palavra["palavra"],
                "nicho": nicho,
                "categoria": palavra["tipo"],
                "tema": tema,
                "score": palavra["score_final"],
                "trace_id": palavra["trace_id"]
            })
        else:
            logger.warning(f"⚠️ Palavra ignorada por dados incompletos: {palavra}")
    return payload

def processar_envio(palavras: list, modo: str, saida: str) -> int:
    start = time()
    trace_id = str(uuid.uuid4())

    tema, nicho = coletar_contexto()
    if not tema or not nicho:
        return 1

    logger.info("➡️  Iniciando validação de palavras...")
    validadas = validar_com_google_planner(palavras, modo=modo, trace_id=trace_id)

    payload = montar_payload(validadas, tema, nicho)

    if payload:
        logger.info(f"🚀 Enviando {len(payload)} palavras ao Prompt Manager...")
        for item in payload:
            logger.info(f"[{item['categoria'].upper()}] {item['palavra_chave']} (Score: {item['score']})")
        exportar_log(payload, trace_id, saida)
        try:
            enviar_ao_prompt_manager(payload)
            logger.info(f"✅ Envio finalizado com sucesso — {len(payload)} palavras entregues.")
        except Exception as e:
            logger.error(f"❌ Erro ao enviar para o Prompt Manager: {e}")
            return 2
    else:
        logger.warning("⚠️ Nenhuma palavra válida para envio.")
        return 3

    logger.info(f"⏱️  Tempo total de execução: {round(time() - start, 2)}s")
    return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Valida palavras-chave e envia ao Prompt Manager.")
    parser.add_argument("--modo", default="mock", choices=["mock", "api"], help="Modo de validação")
    parser.add_argument("--palavras", nargs="+", help="Lista de palavras a validar")
    parser.add_argument("--arquivo", help="Caminho para arquivo .txt com palavras")
    parser.add_argument("--saida", default="envios", help="Diretório onde salvar os logs do envio")
    args = parser.parse_args()

    palavras = args.palavras or []
    if args.arquivo:
        with open(args.arquivo, "r", encoding="utf-8") as f:
            palavras += [linha.strip() for linha in f if linha.strip()]

    if not palavras:
        logger.error("❌ Nenhuma palavra fornecida. Use --palavras ou --arquivo.")
        exit(1)
    else:
        exit(processar_envio(palavras, args.modo, args.saida))
