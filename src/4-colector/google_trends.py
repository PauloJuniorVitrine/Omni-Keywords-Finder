import uuid
import json
import time
import logging
from pathlib import Path
from sqlalchemy.orm import sessionmaker
from database_connection import engine
from theme_manager.utils.lookup_tema_id import get_id_tema
from utils.persistence.coletor_integrator import salvar_coleta

# Simula importações do código original
from ml.trends_ranking import ranquear_trends
from coleta_trends import coletar_dados_do_google
from estrutura.temas import carregar_temas_agendados

# ==============================
# CONFIGURAÇÕES
# ==============================
CONFIG = {
    "NOME_NICHO": "tendencias",
    "ORIGEM": "google_trends",
    "FONTE": "https://trends.google.com",
    "METODO": "trends+ml",
    "ESCOREG_MINIMO": 0.5,
    "DRY_RUN": False,
    "EXPORTAR_JSON": True,
    "OUTPUT_DIR": Path("output/trends/"),
    "CHECKPOINT_PATH": Path("checkpoints/google_trends_falhos.json")
}

# ==============================
# LOGGING
# ==============================
logger = logging.getLogger("google_trends")
logging.basicConfig(level=logging.INFO)

# ==============================
# EXECUÇÃO PRINCIPAL
# ==============================
def executar_google_trends():
    trace_id = str(uuid.uuid4())
    Session = sessionmaker(bind=engine)
    session = Session()

    temas = carregar_temas_agendados()
    falhos = []
    resultados = {}

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
            logger.error(f"[{trace_id}] Erro ao buscar tema '{tema}': {e}")
            falhos.append(tema)
            continue

        try:
            dados = coletar_dados_do_google(tema)
            ranqueadas = ranquear_trends(dados, tema)
            palavras_validas = [p for p, score in ranqueadas if score >= CONFIG["ESCOREG_MINIMO"]]
            resultados[tema] = palavras_validas

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

        except Exception as e:
            logger.error(f"[{trace_id}] Falha ao processar tema '{tema}': {e}")
            falhos.append(tema)

    # Exportar JSON
    if CONFIG["EXPORTAR_JSON"]:
        CONFIG["OUTPUT_DIR"].mkdir(parents=True, exist_ok=True)
        with open(CONFIG["OUTPUT_DIR"] / f"trends_{trace_id}.json", "w", encoding="utf-8") as f:
            json.dump(resultados, f, ensure_ascii=False, indent=2)

    # Checkpoints
    if falhos:
        CONFIG["CHECKPOINT_PATH"].parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG["CHECKPOINT_PATH"], "w", encoding="utf-8") as f:
            json.dump({"falhos": falhos}, f, ensure_ascii=False, indent=2)
        logger.warning(f"[{trace_id}] Temas com falha salvos para reprocessamento: {falhos}")

    logger.info(f"✅ Coleta finalizada com {len(resultados)} temas processados | trace_id={trace_id}")
    session.close()

# ==============================
# EXECUÇÃO DIRETA
# ==============================
if __name__ == "__main__":
    executar_google_trends()
