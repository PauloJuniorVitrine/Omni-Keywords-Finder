import uuid
import json
import logging
import time
from pathlib import Path
from sqlalchemy.orm import sessionmaker
from database_connection import engine
from theme_manager.utils.lookup_tema_id import get_id_tema
from utils.persistence.coletor_integrator import salvar_coleta
from ml.relevance_predictor import prever_relevancia
import spacy

# NLP spaCy
nlp = spacy.load("pt_core_news_md")

def extrair_entidades(texto):
    doc = nlp(texto)
    return [ent.text for ent in doc.ents]

# Logging
logger = logging.getLogger("discord_collector")
logging.basicConfig(level=logging.INFO)

# Configurações
CONFIG = {
    "NOME_NICHO": "comunidades digitais",
    "NOME_TEMA": "discord tendências",
    "ORIGEM": "discord",
    "FONTE": "https://discord.com",
    "METODO": "monitoramento_bot",
    "ESCOREG_MINIMO": 0.5,
    "DRY_RUN": False
}

# Simulador de mensagens capturadas (normalmente viriam de webhooks, logs ou bot)
mensagens = [
    "Como automatizar tarefas no Discord com Python",
    "Melhores bots de moderação para servidores em 2025",
    "Servidores de estudo com inteligência artificial"
]

# Aplicar filtro com ML
def aplicar_modelo_ia(mensagens, tema, origem):
    resultado = []
    for msg in mensagens:
        entidades = extrair_entidades(msg)
        validado, escore = prever_relevancia(msg, tema, origem, entidades)
        if validado and escore >= CONFIG["ESCOREG_MINIMO"]:
            resultado.append(msg)
    return resultado

# Execução principal
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
        logger.error(f"Erro ao obter tema: {e}")
        session.close()
        exit(1)

    mensagens_filtradas = aplicar_modelo_ia(mensagens, CONFIG["NOME_TEMA"], CONFIG["ORIGEM"])

    resultado = salvar_coleta(
        palavras=mensagens_filtradas,
        id_tema=id_tema,
        origem=CONFIG["ORIGEM"],
        fonte=CONFIG["FONTE"],
        metodo=CONFIG["METODO"],
        trace_id=TRACE_ID,
        dry_run=CONFIG["DRY_RUN"]
    )

    logger.info(f"✅ Coletor Discord finalizado com {resultado['quantidade_processada']} mensagens salvas.")
    logger.info(f"⏱️ Tempo total: {round(time.time() - start, 2)}s")
    session.close()
