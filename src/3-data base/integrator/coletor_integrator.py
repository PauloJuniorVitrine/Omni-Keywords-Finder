import uuid
import logging
from datetime import datetime
from database_connection import conectar_banco, cache
from ml.relevance_predictor import prever_relevancia
from keywords.utils.texto_helper import gerar_tags
from prometheus_client import Counter

# === Logger estruturado ===
logger = logging.getLogger("coletor_integrator")

# === Métricas Prometheus ===
palavras_processadas = Counter(
    "palavras_processadas_total",
    "Total de palavras processadas",
    ["tema", "origem"]
)

def salvar_coleta(palavras, id_tema, origem, fonte="", metodo="semantico", dry_run=False, trace_id=None, verbose=True):
    """
    Processa e salva palavras-chave vinculadas a um tema no banco global

    Args:
        palavras (list[str]): Lista de palavras a processar
        id_tema (int): ID do tema (chave estrangeira vinda do Theme Manager)
        origem (str): Nome do coletor ou módulo
        fonte (str): Fonte original (URL, canal, subreddit...)
        metodo (str): Método usado para gerar a palavra ("semantico", "autocomplete", etc)
        dry_run (bool): Se True, não salva no banco (modo de teste)
        trace_id (str): Opcional. Força um trace_id externo para rastreabilidade.
        verbose (bool): Se False, suprime logs detalhados

    Returns:
        dict: Relatório contendo metadados e registros processados
    """
    if not palavras or not isinstance(palavras, list):
        logger.warning("⚠️ Nenhuma palavra recebida ou formato inválido.")
        return {
            "id_tema": id_tema,
            "origem": origem,
            "quantidade_processada": 0,
            "trace_id": trace_id or "",
            "registros": []
        }

    db = conectar_banco()
    resultados = []
    agora = datetime.utcnow().isoformat()
    trace_id = trace_id or str(uuid.uuid4())

    for palavra in palavras:
        palavra = palavra.strip()
        if not palavra:
            logger.warning("⚠️ Palavra em branco ignorada.")
            continue

        try:
            if verbose:
                logger.info(f"🔁 Processando palavra: {palavra}")
            tags = gerar_tags(palavra)
            validado, escore = prever_relevancia(palavra, id_tema, origem, tags)

            dados = {
                "id_tema": id_tema,
                "origem": origem,
                "palavra": palavra,
                "tags": ",".join(tags),
                "escore": round(escore, 4),
                "validado": validado,
                "trace_id": trace_id,
                "criado_em": agora,
                "fonte": fonte,
                "metodo_geracao": metodo
            }

            if not dry_run:
                db.executar_modificacao("""
                    INSERT INTO palavras_chave (
                        id_tema, origem, palavra, tags, escore, validado, trace_id, criado_em, fonte, metodo_geracao
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, tuple(dados.values()))

                if cache:
                    cache_key = f"chave:{palavra}"
                    cache.hmset(cache_key, dados)
                    cache.expire(cache_key, 86400)

            resultados.append(dados)
            if verbose:
                logger.info(f"✅ Palavra salva: {palavra} | Tema ID: {id_tema} | Origem: {origem}")

            # Atualiza métrica Prometheus
            palavras_processadas.labels(tema=str(id_tema), origem=origem).inc()

        except Exception as e:
            logger.error(f"❌ Falha ao salvar '{palavra}': {e}", exc_info=True)

    if verbose:
        logger.info(f"📦 Total processado: {len(resultados)} palavras | Tema ID: {id_tema} | Trace ID: {trace_id}")

    return {
        "id_tema": id_tema,
        "origem": origem,
        "quantidade_processada": len(resultados),
        "trace_id": trace_id,
        "registros": resultados
    }
