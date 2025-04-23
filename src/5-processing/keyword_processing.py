# processing/keyword_processing.py

import re
import random
import logging
from typing import List, Dict, Union, Optional, Tuple
from pathlib import Path
from uuid import uuid4

import spacy
from redis import Redis

from theme_manager.ml_model import prever_relevancia
from theme_manager.utils.score import calcular_score
from theme_manager.config import (
    CONCORRENCIA_ACEITA_DEFAULT,
    VOLUME_MIN_DEFAULT,
    SCORE_MIN_DEFAULT
)

logger = logging.getLogger(__name__)
nlp = spacy.load("pt_core_news_sm")

# ---------------------------
# Logger com trace_id
# ---------------------------
def log_info(msg: str, trace_id: Optional[str] = None):
    logger.info(f"[{trace_id}] {msg}" if trace_id else msg)

def log_warn(msg: str, trace_id: Optional[str] = None):
    logger.warning(f"[{trace_id}] {msg}" if trace_id else msg)

def log_error(msg: str, trace_id: Optional[str] = None):
    logger.error(f"[{trace_id}] {msg}" if trace_id else msg)

# ---------------------------
# Função 1 - Normalização
# ---------------------------
def normalizar_palavra(palavra: str) -> str:
    if not isinstance(palavra, str):
        raise ValueError("A palavra deve ser uma string.")
    return re.sub(r"[^a-zA-Z0-9çáéíóúãõâêîôûÀ-ÿ\s]", "", palavra.strip().lower())

# ---------------------------
# Função 2 - Geração de Tags
# ---------------------------
def gerar_tags(texto: str) -> List[str]:
    if not isinstance(texto, str):
        raise ValueError("Texto para geração de tags deve ser uma string.")
    doc = nlp(texto)
    return list(set(ent.text.lower() for ent in doc.ents if len(ent.text) > 2))

# ---------------------------
# Função 3 - Filtragem por critérios semânticos
# ---------------------------
def filtrar_keywords(
    lista: List[Dict],
    concorrencia_aceita: List[str] = CONCORRENCIA_ACEITA_DEFAULT,
    palavras_excluidas: List[str] = [],
    volume_min: int = VOLUME_MIN_DEFAULT,
    score_min: float = SCORE_MIN_DEFAULT
) -> List[Dict]:
    if not isinstance(lista, list):
        raise ValueError("A lista de palavras-chave deve ser uma lista de dicionários.")
    resultado = []
    for item in lista:
        palavra = item.get("palavra", "")
        if item.get("concorrencia") not in concorrencia_aceita:
            continue
        if any(exc.lower() in palavra.lower() for exc in palavras_excluidas):
            continue
        if item.get("volume", 0) < volume_min:
            continue
        if item.get("score_final", 0) < score_min:
            continue
        resultado.append(item)
    return resultado

# ---------------------------
# Função 4 - Validação com Google Planner (mock ou API futura)
# ---------------------------
def validar_keywords_com_google_planner(
    palavras: List[str],
    trace_id: Optional[str] = None,
    volume_min: int = VOLUME_MIN_DEFAULT,
    score_min: float = SCORE_MIN_DEFAULT,
    modo: str = "mock"
) -> List[Dict]:
    if modo != "mock":
        raise NotImplementedError("Integração real com Google Planner não implementada.")

    if not palavras or not all(isinstance(p, str) and p.strip() for p in palavras):
        raise ValueError("Lista de palavras inválida.")

    trace = trace_id or f"TRACE-{uuid4()}"
    resultado = []
    for palavra in palavras:
        try:
            palavra_norm = normalizar_palavra(palavra)
            volume = random.randint(100, 5000)
            cpc = round(random.uniform(0.5, 5.0), 2)
            score = calcular_score(volume, cpc)
            if score >= score_min and volume >= volume_min:
                resultado.append({
                    "palavra": palavra_norm,
                    "volume": volume,
                    "cpc": cpc,
                    "score_final": score,
                    "concorrencia": "baixa" if cpc < 1.5 else "média",
                    "trace_id": trace
                })
        except Exception as e:
            log_warn(f"Erro ao validar palavra '{palavra}': {e}", trace)
    return resultado

# ---------------------------
# Função 5 - Previsão de relevância com ML
# ---------------------------
def classificar_relevancia(palavra: str, tags: Optional[List[str]] = None) -> Tuple[bool, float]:
    if not isinstance(palavra, str):
        raise ValueError("A palavra deve ser uma string.")
    try:
        return prever_relevancia(palavra, tags)
    except Exception as e:
        log_warn(f"Erro na classificação da palavra '{palavra}': {e}")
        return False, 0.0

# ---------------------------
# Função 6 - Pipeline completo (reutilizável)
# ---------------------------
def pipeline_keywords(
    palavras: List[str],
    modo_validador: str = "mock",
    volume_min: int = VOLUME_MIN_DEFAULT,
    score_min: float = SCORE_MIN_DEFAULT,
    palavras_excluidas: List[str] = [],
    concorrencia_aceita: List[str] = CONCORRENCIA_ACEITA_DEFAULT,
    dry_run: bool = False,
    trace_id: Optional[str] = None
) -> Dict[str, Union[str, List, Dict]]:
    if not isinstance(palavras, list):
        raise ValueError("A lista de palavras deve ser uma lista de strings.")

    trace = trace_id or f"TRACE-{uuid4()}"
    log_info("Iniciando pipeline de palavras-chave", trace)

    validas = validar_keywords_com_google_planner(
        palavras, trace, volume_min, score_min, modo=modo_validador
    )

    filtradas = filtrar_keywords(
        validas,
        concorrencia_aceita=concorrencia_aceita,
        palavras_excluidas=palavras_excluidas,
        volume_min=volume_min,
        score_min=score_min
    )

    aprovadas = []
    reprovadas = []
    for item in filtradas:
        try:
            tags = gerar_tags(item["palavra"])
            aprovado, score = classificar_relevancia(item["palavra"], tags)
            if aprovado:
                aprovadas.append(item)
            else:
                reprovadas.append(item["palavra"])
        except Exception as e:
            log_error(f"Erro ao classificar palavra '{item.get('palavra')}': {e}", trace)
            reprovadas.append(item.get("palavra", ""))

    log_info(f"Pipeline finalizado. Aprovadas: {len(aprovadas)}, Reprovadas: {len(reprovadas)}", trace)

    if dry_run:
        log_warn("Modo dry-run: nenhuma palavra foi persistida", trace)

    return {
        "aprovadas": aprovadas,
        "reprovadas": reprovadas,
        "trace_id": trace,
        "metrics": {
            "total": len(palavras),
            "validadas": len(validas),
            "filtradas": len(filtradas),
            "aprovadas": len(aprovadas),
            "reprovadas": len(reprovadas),
        }
    }
