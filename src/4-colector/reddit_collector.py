import uuid
import json
import time
import logging
import csv
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from sqlalchemy.orm import sessionmaker
from database_connection import engine
from theme_manager.utils.lookup_tema_id import get_id_tema
from utils.persistence.coletor_integrator import salvar_coleta
from ml.relevance_predictor import prever_relevancia
import spacy

# =========================
# CONFIG
# =========================
CONFIG = {
    "NOME_NICHO": "tecnologia",
    "ORIGEM": "reddit",
    "FONTE": "https://www.reddit.com",
    "METODO": "scraper_reddit",
    "ESCOREG_MINIMO": 0.5,
    "DRY_RUN": False,
    "EXPORTAR_CSV": True,
    "EXPORTAR_NDJSON": True,
    "OUTPUT_DIR": Path("output/reddit/"),
    "CHECKPOINT_PATH": Path("checkpoints/reddit_falhos.json"),
    "TEMAS_PATH": Path("themes_agendados.json")
}

# =========================
# LOGGING E NLP
# =========================
logger = logging.getLogger("reddit_collector")
logging.basicConfig(level=logging.INFO)
nlp = spacy.load("pt_core_news_md")

def gerar_tags(texto):
    doc = nlp(texto)
    return list(set([ent.text.lower() for ent in doc.ents]))

# =========================
# FUNÇÃO DE COLETA (simulada)
# =========================
def coletar_titulos_reddit(tema):
    url = f"https://www.reddit.com/search/?q={requests.utils.quote(tema)}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            logger.warning(f"Erro HTTP {response.status_code} para o tema: {tema}")
            return []
        soup = BeautifulSoup(response.text, "html.parser")
        return [tag.get_text(strip=True) for tag in soup.find_all("h3") if tag.get_text(strip=True)]
    except Exception as e:
        logger.error(f"Erro ao buscar no Reddit: {e}")
        return []

# =========================
# EXECUÇÃO PRINCIPAL
# =========================
def executar_reddit():
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

        titulos = coletar_titulos_reddit(tema)
        palavras_validadas = []

        for titulo in titulos:
            tags = gerar_tags(titulo)
            validado, escore = prever_relevancia(titulo, tema, CONFIG["ORIGEM"], tags)
            if validado and escore >= CONFIG["ESCOREG_MINIMO"]:
                palavras_validadas.append(titulo)

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

        time.sleep(1)

    session.close()
    CONFIG["OUTPUT_DIR"].mkdir(parents=True, exist_ok=True)

    if CONFIG["EXPORTAR_CSV"]:
        with open(CONFIG["OUTPUT_DIR"] / f"reddit_keywords_{trace_id}.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["tema", "keyword"])
            for tema, palavras in resultados.items():
                for palavra in palavras:
                    writer.writerow([tema, palavra])

    if CONFIG["EXPORTAR_NDJSON"]:
        with open(CONFIG["OUTPUT_DIR"] / f"reddit_keywords_{trace_id}.ndjson", "w", encoding="utf-8") as f:
            for tema, palavras in resultados.items():
                for palavra in palavras:
                    f.write(json.dumps({"tema": tema, "keyword": palavra}) + "\n")

    if falhos:
        CONFIG["CHECKPOINT_PATH"].parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG["CHECKPOINT_PATH"], "w", encoding="utf-8") as f:
            json.dump({"falhos": falhos}, f, ensure_ascii=False, indent=2)
        logger.warning(f"Temas com falha salvos para reprocessamento: {falhos}")

    logger.info(f"✅ Coleta Reddit finalizada com {len(resultados)} temas processados | trace_id={trace_id}")

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    executar_reddit()
