import uuid
import json
import time
import logging
import csv
import requests
from pathlib import Path
from urllib.parse import quote
from sqlalchemy.orm import sessionmaker
from database_connection import engine
from theme_manager.utils.lookup_tema_id import get_id_tema
from utils.persistence.coletor_integrator import salvar_coleta
from ml.autocomplete_ranker import ranquear_sugestoes

# =========================
# CONFIGURAÇÕES GLOBAIS
# =========================
CONFIG = {
    "NOME_NICHO": "seo",
    "ORIGEM": "google_autocomplete",
    "FONTE": "https://suggestqueries.google.com",
    "METODO": "autocomplete+ml",
    "ESCOREG_MINIMO": 0.5,
    "DRY_RUN": False,
    "CHECKPOINT_PATH": Path("checkpoints/google_autocomplete_falhos.json"),
    "EXPORTAR_JSON": True,
    "EXPORTAR_NDJSON": True,
    "EXPORTAR_CSV": True,
    "WEBHOOK_URL": "",
    "MAX_RETRIES": 3,
    "BACKOFF_BASE": 2
}

# =========================
# LOGGING
# =========================
logger = logging.getLogger("google_autocomplete")
logging.basicConfig(level=logging.INFO)

# =========================
# WEBHOOK
# =========================
def notificar_webhook(mensagem, trace_id):
    url = CONFIG.get("WEBHOOK_URL")
    if url:
        try:
            requests.post(url, json={"text": f"{mensagem} | Trace ID: {trace_id}"})
        except Exception as e:
            logger.warning(f"Erro ao enviar webhook: {e}")

# =========================
# FUNÇÃO DE COLETA COM RETRY E BACKOFF
# =========================
def buscar_sugestoes(termo):
    url = f"https://suggestqueries.google.com/complete/search?client=firefox&q={quote(termo)}"
    for tentativa in range(CONFIG["MAX_RETRIES"]):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()[1]
            elif response.status_code in (403, 429):
                logger.warning(f"[{termo}] Bloqueio detectado: {response.status_code}. Cooldown...")
                time.sleep(60 * (tentativa + 1))
            else:
                logger.warning(f"[{termo}] Erro HTTP {response.status_code}")
        except Exception as e:
            logger.error(f"[{termo}] Erro de rede: {e}")
        backoff = CONFIG["BACKOFF_BASE"] ** tentativa
        time.sleep(backoff)
    return []

# =========================
# EXECUÇÃO PRINCIPAL
# =========================
def executar_autocomplete(temas):
    trace_id = str(uuid.uuid4())
    Session = sessionmaker(bind=engine)
    session = Session()
    resultados_gerais = {}
    falhos = []

    output_base = f"output/autocomplete_{trace_id}"
    json_path = Path(f"{output_base}.json")
    ndjson_path = Path(f"{output_base}.ndjson")
    csv_path = Path(f"{output_base}.csv")

    for tema in temas:
        try:
            id_tema = get_id_tema(
                session=session,
                nome_nicho=CONFIG["NOME_NICHO"],
                nome_tema=tema,
                criar_se_nao_existir=True,
                trace_id=trace_id
            )
        except ValueError as e:
            logger.error(f"[{trace_id}] Erro ao obter tema '{tema}': {e}")
            falhos.append(tema)
            continue

        sugestoes = buscar_sugestoes(tema)
        if not sugestoes:
            falhos.append(tema)
            continue

        ranqueadas = ranquear_sugestoes(sugestoes, tema, CONFIG["ORIGEM"])
        palavras_validas = [p for p, score in ranqueadas if score >= CONFIG["ESCOREG_MINIMO"]]
        escores = [score for _, score in ranqueadas if score >= CONFIG["ESCOREG_MINIMO"]]
        media = round(sum(escores) / len(escores), 3) if escores else 0

        logger.info(f"[{trace_id}] Tema '{tema}' - escore médio: {media} - total: {len(palavras_validas)}")

        salvar_coleta(
            palavras=palavras_validas,
            id_tema=id_tema,
            origem=CONFIG["ORIGEM"],
            fonte=CONFIG["FONTE"],
            metodo=CONFIG["METODO"],
            trace_id=trace_id,
            dry_run=CONFIG["DRY_RUN"]
        )

        resultados_gerais[tema] = palavras_validas
        time.sleep(1)

    Path("output").mkdir(parents=True, exist_ok=True)

    if CONFIG["EXPORTAR_JSON"]:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(resultados_gerais, f, ensure_ascii=False, indent=2)

    if CONFIG["EXPORTAR_NDJSON"]:
        with open(ndjson_path, "w", encoding="utf-8") as f:
            for tema, palavras in resultados_gerais.items():
                for palavra in palavras:
                    f.write(json.dumps({"tema": tema, "keyword": palavra}) + "\n")

    if CONFIG["EXPORTAR_CSV"]:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["tema", "keyword"])
            for tema, palavras in resultados_gerais.items():
                for palavra in palavras:
                    writer.writerow([tema, palavra])

    if falhos:
        CONFIG["CHECKPOINT_PATH"].parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG["CHECKPOINT_PATH"], "w", encoding="utf-8") as f:
            json.dump({"falhos": falhos}, f, ensure_ascii=False, indent=2)
        logger.warning(f"Temas com falha salvos para reprocessamento: {falhos}")

    logger.info(f"✅ Coleta concluída com {len(resultados_gerais)} temas processados | trace_id={trace_id}")
    notificar_webhook("✅ Coleta Google Autocomplete finalizada", trace_id)
    session.close()

# =========================
# RODAR COLETA
# =========================
if __name__ == "__main__":
    temas = [
        "estratégia de conteúdo",
        "funil de vendas",
        "palavras-chave long tail"
    ]
    executar_autocomplete(temas)
