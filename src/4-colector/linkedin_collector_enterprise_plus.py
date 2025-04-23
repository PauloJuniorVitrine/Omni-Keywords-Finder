import uuid
import json
import time
import logging
import csv
import requests
from pathlib import Path
from sqlalchemy.orm import sessionmaker
from database_connection import engine
from theme_manager.utils.lookup_tema_id import get_id_tema
from utils.persistence.coletor_integrator import salvar_coleta
from ml.relevance_predictor import prever_relevancia
import spacy

# =========================
# CONFIGURAÇÃO GLOBAL
# =========================
CONFIG = {
    "NOME_NICHO": "negocios",
    "NOME_TEMA": "tendencias linkedin",
    "ORIGEM": "linkedin",
    "FONTE": "https://www.linkedin.com",
    "METODO": "linkedin_scraper",
    "ESCOREG_MINIMO": 0.5,
    "DRY_RUN": False,
    "EXPORTAR_CSV": True,
    "EXPORTAR_NDJSON": True,
    "CHECKPOINT_PATH": Path("checkpoints/linkedin_falhos.json"),
    "OUTPUT_DIR": Path("output/linkedin/")
}

# =========================
# LOGGING E NLP
# =========================
logger = logging.getLogger("linkedin_collector")
logging.basicConfig(level=logging.INFO)
nlp = spacy.load("pt_core_news_md")

def extrair_tags(texto):
    doc = nlp(texto)
    return list(set([ent.text.lower() for ent in doc.ents]))

# =========================
# COLETA SIMULADA
# =========================
def simular_postagens_linkedin():
    return [
        "5 estratégias de liderança em ambientes híbridos",
        "Como a inteligência artificial está mudando o RH",
        "Tendências de marketing B2B para 2025"
    ]

# =========================
# EXECUÇÃO PRINCIPAL
# =========================
def executar_coleta_linkedin():
    trace_id = str(uuid.uuid4())
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        id_tema = get_id_tema(
            session=session,
            nome_nicho=CONFIG["NOME_NICHO"],
            nome_tema=CONFIG["NOME_TEMA"],
            criar_se_nao_existir=True,
            trace_id=trace_id
        )
    except ValueError as e:
        logger.error(f"[{trace_id}] Erro ao obter tema: {e}")
        session.close()
        return

    posts = simular_postagens_linkedin()
    palavras_validas = []

    for post in posts:
        tags = extrair_tags(post)
        validado, escore = prever_relevancia(post, CONFIG["NOME_TEMA"], CONFIG["ORIGEM"], tags)
        if validado and escore >= CONFIG["ESCOREG_MINIMO"]:
            palavras_validas.append(post)

    if not CONFIG["DRY_RUN"]:
        salvar_coleta(
            palavras=palavras_validas,
            id_tema=id_tema,
            origem=CONFIG["ORIGEM"],
            fonte=CONFIG["FONTE"],
            metodo=CONFIG["METODO"],
            trace_id=trace_id,
            dry_run=False
        )

    CONFIG["OUTPUT_DIR"].mkdir(parents=True, exist_ok=True)

    if CONFIG["EXPORTAR_CSV"]:
        with open(CONFIG["OUTPUT_DIR"] / f"linkedin_keywords_{trace_id}.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["keyword"])
            for palavra in palavras_validas:
                writer.writerow([palavra])

    if CONFIG["EXPORTAR_NDJSON"]:
        with open(CONFIG["OUTPUT_DIR"] / f"linkedin_keywords_{trace_id}.ndjson", "w", encoding="utf-8") as f:
            for palavra in palavras_validas:
                f.write(json.dumps({"keyword": palavra}) + "\n")

    logger.info(f"✅ Coleta LinkedIn finalizada com {len(palavras_validas)} palavras válidas | trace_id={trace_id}")
    session.close()

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    executar_coleta_linkedin()
