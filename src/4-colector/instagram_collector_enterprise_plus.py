import uuid
import json
import time
import logging
import csv
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential
from sqlalchemy.orm import sessionmaker
from database_connection import engine
from theme_manager.utils.lookup_tema_id import get_id_tema
from utils.persistence.coletor_integrator import salvar_coleta
from ml.relevance_predictor import prever_relevancia
import spacy

# =========================
# CONFIGURAÇÕES
# =========================
CONFIG = {
    "NOME_NICHO": "marketing",
    "ORIGEM": "instagram",
    "FONTE": "https://www.instagram.com",
    "METODO": "scraper_instagram",
    "ESCOREG_MINIMO": 0.5,
    "DRY_RUN": False,
    "EXPORTAR_CSV": True,
    "EXPORTAR_NDJSON": True,
    "OUTPUT_DIR": Path("output/instagram/"),
    "CHECKPOINT_PATH": Path("checkpoints/instagram_falhos.json"),
    "TEMAS_PATH": Path("themes_agendados.json"),
    "WEBHOOK_URL": ""
}

# =========================
# LOGGING E NLP
# =========================
logger = logging.getLogger("instagram_collector")
logging.basicConfig(level=logging.INFO)
nlp = spacy.load("pt_core_news_md")

def gerar_tags(texto):
    doc = nlp(texto)
    return list(set([ent.text.lower() for ent in doc.ents]))

# =========================
# WEBHOOK
# =========================
def enviar_webhook(payload):
    if not CONFIG["WEBHOOK_URL"]:
        return
    try:
        requests.post(CONFIG["WEBHOOK_URL"], json=payload, timeout=5)
    except Exception as e:
        logger.warning(f"Falha ao enviar webhook: {e}")

# =========================
# COLETA DE HASHTAGS INSTAGRAM
# =========================
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def coletar_tendencias_instagram(tema):
    headers = {"User-Agent": "Mozilla/5.0"}
    url = f"https://www.instagram.com/explore/tags/{tema.replace(' ', '')}/"
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code != 200:
        raise Exception(f"Erro HTTP {response.status_code} para o tema: {tema}")
    if "login" in response.url or "captcha" in response.text.lower():
        raise Exception("Detectado possível bloqueio ou CAPTCHA")
    soup = BeautifulSoup(response.text, "html.parser")
    return [
        tag.get_text(strip=True)
        for tag in soup.find_all("span") if tag.get_text(strip=True).startswith("#")
    ]

# =========================
# EXECUÇÃO PRINCIPAL
# =========================
def executar_instagram():
    trace_id = str(uuid.uuid4())
    resultados = {}
    falhos = []

    if not CONFIG["TEMAS_PATH"].exists():
        logger.error("Arquivo de temas não encontrado.")
        return

    with open(CONFIG["TEMAS_PATH"], "r", encoding="utf-8") as f:
        temas = json.load(f)

    Session = sessionmaker(bind=engine)
    session = Session()

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

        try:
            hashtags = coletar_tendencias_instagram(tema)
        except Exception as e:
            logger.error(f"[{trace_id}] Falha na coleta do tema '{tema}': {e}")
            falhos.append(tema)
            continue

        palavras_validadas = []
        for hashtag in hashtags:
            tags = gerar_tags(hashtag)
            validado, escore = prever_relevancia(hashtag, tema, CONFIG["ORIGEM"], tags)
            if validado and escore >= CONFIG["ESCOREG_MINIMO"]:
                palavras_validadas.append(hashtag)

        resultados[tema] = palavras_validadas

        if not CONFIG["DRY_RUN"]:
            salvar_coleta(
                palavras=palavras_validadas,
                id_tema=id_tema,
                origem=CONFIG["ORIGEM"],
                fonte=CONFIG["FONTE"],
                metodo=CONFIG["METODO"],
                trace_id=trace_id,
                dry_run=False
            )

        enviar_webhook({"evento": "coleta_concluida", "tema": tema, "quantidade": len(palavras_validadas), "trace_id": trace_id})
        time.sleep(1)

    session.close()
    CONFIG["OUTPUT_DIR"].mkdir(parents=True, exist_ok=True)

    if CONFIG["EXPORTAR_CSV"]:
        with open(CONFIG["OUTPUT_DIR"] / f"instagram_keywords_{trace_id}.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["tema", "keyword"])
            for tema, palavras in resultados.items():
                for palavra in palavras:
                    writer.writerow([tema, palavra])

    if CONFIG["EXPORTAR_NDJSON"]:
        with open(CONFIG["OUTPUT_DIR"] / f"instagram_keywords_{trace_id}.ndjson", "w", encoding="utf-8") as f:
            for tema, palavras in resultados.items():
                for palavra in palavras:
                    f.write(json.dumps({"tema": tema, "keyword": palavra}) + "\n")

    if falhos:
        CONFIG["CHECKPOINT_PATH"].parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG["CHECKPOINT_PATH"], "w", encoding="utf-8") as f:
            json.dump({"falhos": falhos}, f, ensure_ascii=False, indent=2)
        logger.warning(f"Temas com falha salvos para reprocessamento: {falhos}")

    logger.info(f"✅ Coleta Instagram finalizada com {len(resultados)} temas processados | trace_id={trace_id}")
    enviar_webhook({"evento": "execucao_finalizada", "sucesso": len(resultados), "falhas": len(falhos), "trace_id": trace_id})

# =========================
# EXECUÇÃO DIRETA
# =========================
if __name__ == "__main__":
    executar_instagram()
