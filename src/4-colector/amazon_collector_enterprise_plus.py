import uuid
import json
import time
import logging
import random
from pathlib import Path
from bs4 import BeautifulSoup
import requests
import spacy
from sqlalchemy.orm import sessionmaker
from database_connection import engine
from theme_manager.utils.lookup_tema_id import get_id_tema
from utils.persistence.coletor_integrator import salvar_coleta
from ml.relevance_predictor import prever_relevancia

# =========================
# CONFIGURAÇÕES GLOBAIS
# =========================
CONFIG = {
    "NOME_NICHO": "ecommerce",
    "NOME_TEMA": "produtos amazon",
    "ORIGEM": "amazon",
    "FONTE": "https://www.amazon.com",
    "METODO": "scraper_amazon",
    "LIMIT_POR_CONSULTA": 10,
    "ESCOREG_MINIMO": 0.5,
    "TIMEOUT": 10,
    "MAX_RETRIES": 3,
    "DRY_RUN": False,
    "EXPORTAR_JSON": True,
    "EXPORTAR_NDJSON": True,
    "EXPORTAR_CSV": True,
    "WEBHOOK_URL": "",
    "CHECKPOINT_PATH": Path("checkpoints/amazon_falhos.json")
}

# =========================
# LOGGING
# =========================
logger = logging.getLogger("amazon_collector")
logging.basicConfig(level=logging.INFO)

# =========================
# NLP spaCy
# =========================
nlp = spacy.load("pt_core_news_md")

def extrair_entidades(texto):
    doc = nlp(texto)
    return [ent.text for ent in doc.ents]

# =========================
# USER AGENTS ROTATIVOS
# =========================
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/114.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/91.0"
]

# =========================
# FUNÇÕES DE SCRAPING
# =========================
def extrair_titulos_amazon(consulta: str, limite: int):
    url = f"https://www.amazon.com/s?k={consulta.replace(' ', '+')}"
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    for tentativa in range(CONFIG["MAX_RETRIES"]):
        try:
            response = requests.get(url, headers=headers, timeout=CONFIG["TIMEOUT"])
            if response.status_code == 403 or "captcha" in response.text.lower():
                logger.warning(f"🔐 Bloqueio detectado para '{consulta}' (403/CAPTCHA)")
                time.sleep(300)  # cooldown de 5 min
                return []
            if response.status_code != 200:
                logger.warning(f"⚠️ Falha na requisição ({response.status_code}) [{consulta}]")
                time.sleep(2 ** tentativa)
                continue

            soup = BeautifulSoup(response.text, "html.parser")
            return [item.get_text(strip=True) for item in soup.select("h2 a span")[:limite]]

        except requests.RequestException as e:
            logger.error(f"Erro de rede: {e}")
            time.sleep(2 ** tentativa)
    return []

# =========================
# FILTRAGEM COM IA
# =========================
def aplicar_modelo_ia(palavras, tema, origem):
    resultados_filtrados = []
    for palavra in palavras:
        entidades = extrair_entidades(palavra)
        validado, escore = prever_relevancia(palavra, tema, origem, entidades)
        if validado and escore >= CONFIG["ESCOREG_MINIMO"]:
            resultados_filtrados.append(palavra)
    return resultados_filtrados

# =========================
# EXECUÇÃO PRINCIPAL
# =========================
def executar_coleta_amazon(consultas):
    palavras_totais = []
    termos_falhos = []
    for termo in consultas:
        logger.info(f"🔎 Coletando para termo: {termo} | trace_id={TRACE_ID}")
        titulos = extrair_titulos_amazon(termo, CONFIG["LIMIT_POR_CONSULTA"])
        if not titulos:
            termos_falhos.append(termo)
            continue
        palavras_validas = aplicar_modelo_ia(titulos, CONFIG["NOME_TEMA"], CONFIG["ORIGEM"])
        palavras_totais.extend(palavras_validas)
        time.sleep(1)

    if termos_falhos:
        CONFIG["CHECKPOINT_PATH"].parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG["CHECKPOINT_PATH"], "w", encoding="utf-8") as f:
            json.dump({"falhos": termos_falhos}, f, ensure_ascii=False, indent=2)
        logger.warning(f"⚠️ Termos com falha salvos para reprocessamento: {termos_falhos}")

    return palavras_totais

# =========================
# NOTIFICAÇÃO WEBHOOK
# =========================
def notificar_webhook(mensagem):
    url = CONFIG.get("WEBHOOK_URL")
    if url:
        try:
            requests.post(url, json={"text": mensagem})
        except Exception as e:
            logger.warning(f"Erro ao enviar webhook: {e}")

# =========================
# FLUXO DE EXECUÇÃO
# =========================
if __name__ == "__main__":
    start = time.time()
    TRACE_ID = str(uuid.uuid4())
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        id_tema = get_id_tema(
            session=session,
            nome_nicho=CONFIG["NOME_NICHO"],
            nome_tema=CONFIG["NOME_TEMA"],
            criar_se_nao_existir=True,
            trace_id=TRACE_ID
        )
    except ValueError as e:
        logger.error(f"❌ Erro ao obter tema: {e}")
        session.close()
        exit(1)

    consultas = ["notebooks", "smartphones", "gadgets"]
    palavras_extraidas = executar_coleta_amazon(consultas)

    Path("output").mkdir(exist_ok=True)

    if CONFIG["EXPORTAR_JSON"]:
        with open("output/amazon_keywords.json", "w", encoding="utf-8") as f:
            json.dump(palavras_extraidas, f, ensure_ascii=False, indent=2)

    if CONFIG["EXPORTAR_NDJSON"]:
        with open("output/amazon_keywords.ndjson", "w", encoding="utf-8") as f:
            for palavra in palavras_extraidas:
                f.write(json.dumps({"keyword": palavra}) + "\n")

    if CONFIG["EXPORTAR_CSV"]:
        import csv
        with open("output/amazon_keywords.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["palavra"])
            for palavra in palavras_extraidas:
                writer.writerow([palavra])

    resultado = salvar_coleta(
        palavras=palavras_extraidas,
        id_tema=id_tema,
        origem=CONFIG["ORIGEM"],
        fonte=CONFIG["FONTE"],
        metodo=CONFIG["METODO"],
        trace_id=TRACE_ID,
        dry_run=CONFIG["DRY_RUN"]
    )

    logger.info(f"✅ Coleta finalizada: {resultado['quantidade_processada']} palavras | trace_id={TRACE_ID}")
    logger.info(f"⏱️ Tempo total: {round(time.time() - start, 2)}s")
    notificar_webhook(f"✅ Coletor Amazon finalizado com {resultado['quantidade_processada']} palavras. Trace ID: {TRACE_ID}")
    session.close()
