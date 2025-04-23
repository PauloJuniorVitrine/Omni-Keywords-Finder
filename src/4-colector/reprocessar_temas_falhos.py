import json
import uuid
import logging
from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import sessionmaker
from database_connection import engine
from theme_manager.utils.lookup_tema_id import get_id_tema
from utils.persistence.coletor_integrator import salvar_coleta

TRACE_ID = str(uuid.uuid4())
logger = logging.getLogger("reprocessador")
logging.basicConfig(level=logging.INFO)

# ==========================
# CONFIGURAÇÕES
# ==========================
CONFIG = {
    "NOME_NICHO": "geral",
    "CAMINHO_FALHOS": Path("checkpoints/temas_falhos.json"),
    "CAMINHO_VARIACOES": Path("variacoes_geradas"),
    "EXPORTAR_JSON": True,
    "EXPORTAR_CSV": True,
    "ORIGEM": "reprocessador",
    "FONTE": "variações_cauda_longa",
    "METODO": "reprocessamento_falhos"
}

# ==========================
# FUNÇÃO FAKE PARA TESTE
# ==========================
def gerar_variacoes(tema):
    return [
        f"como usar {tema} em 2024",
        f"tendências de {tema} para empresas",
        f"dicas de especialistas sobre {tema}"
    ]

# ==========================
# EXECUÇÃO PRINCIPAL
# ==========================
def reprocessar_temas():
    if not CONFIG["CAMINHO_FALHOS"].exists():
        logger.error("Arquivo de temas falhos não encontrado.")
        return

    with open(CONFIG["CAMINHO_FALHOS"], "r", encoding="utf-8") as f:
        data = json.load(f)

    temas = data.get("falhos", [])
    if not temas:
        logger.info("Nenhum tema para reprocessar.")
        return

    Session = sessionmaker(bind=engine)
    session = Session()
    resultados = {}
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")

    for tema in temas:
        try:
            id_tema = get_id_tema(
                session=session,
                nome_nicho=CONFIG["NOME_NICHO"],
                nome_tema=tema,
                criar_se_nao_existir=True,
                trace_id=TRACE_ID
            )
        except Exception as e:
            logger.error(f"[{TRACE_ID}] Falha ao buscar id_tema para '{tema}': {e}")
            continue

        try:
            palavras = gerar_variacoes(tema)
            resultados[tema] = palavras

            salvar_coleta(
                palavras=palavras,
                id_tema=id_tema,
                origem=CONFIG["ORIGEM"],
                fonte=CONFIG["FONTE"],
                metodo=CONFIG["METODO"],
                trace_id=TRACE_ID,
                dry_run=False
            )

        except Exception as e:
            logger.error(f"[{TRACE_ID}] Erro ao salvar coleta de '{tema}': {e}")

    session.close()

    CONFIG["CAMINHO_VARIACOES"].mkdir(parents=True, exist_ok=True)
    if CONFIG["EXPORTAR_JSON"]:
        with open(CONFIG["CAMINHO_VARIACOES"] / f"variacoes_{now_str}.json", "w", encoding="utf-8") as f:
            json.dump(resultados, f, ensure_ascii=False, indent=2)

    if CONFIG["EXPORTAR_CSV"]:
        with open(CONFIG["CAMINHO_VARIACOES"] / f"variacoes_{now_str}.csv", "w", encoding="utf-8") as f:
            f.write("tema,keyword\n")
            for tema, palavras in resultados.items():
                for palavra in palavras:
                    f.write(f"{tema},{palavra}\n")

    logger.info(f"✅ Reprocessamento concluído com sucesso | trace_id={TRACE_ID}")

# ==========================
# MAIN
# ==========================
if __name__ == "__main__":
    reprocessar_temas()
