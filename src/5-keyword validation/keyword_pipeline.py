import logging
import uuid
import time
import json
from pathlib import Path
from sqlalchemy.orm import sessionmaker
from database_connection import engine
from models import PalavraChave
from keyword_validation.google_planner_validator import validar_keywords_com_google_planner
from keyword_validation.filter_keywords import filtrar_keywords

# =============================
# CONFIGURAÇÃO E LOGGING
# =============================
logger = logging.getLogger("keyword_pipeline")
logging.basicConfig(level=logging.INFO)

EXPORT_DIR = Path("output/validacao_google/")
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

# =============================
# CARREGA PALAVRAS DO BANCO
# =============================
def carregar_palavras(session, limite=500) -> list[str]:
    palavras_query = session.query(PalavraChave).filter(
        PalavraChave.status == "validado",
        PalavraChave.volume_google.is_(None)
    ).limit(limite)
    palavras = [p.palavra for p in palavras_query.all() if p.palavra]
    logger.info(f"🔍 {len(palavras)} palavras carregadas do banco para validação.")
    return palavras

# =============================
# ATUALIZA NO BANCO AS PALAVRAS VALIDADAS
# =============================
def atualizar_palavra(session, resultado, trace_id):
    palavra = resultado['palavra']
    registro = session.query(PalavraChave).filter_by(palavra=palavra).first()
    if registro:
        registro.volume_google = resultado['volume']
        registro.cpc = resultado['cpc']
        registro.concorrencia = resultado['concorrencia']
        registro.score_final = resultado['score_final']
        registro.status = 'aprovada_prompt'
        registro.trace_id = trace_id

# =============================
# ENVIAR AO PROMPT MANAGER (simulado)
# =============================
def enviar_ao_prompt_manager(keywords_validadas: list[dict]):
    for k in keywords_validadas:
        logger.info(f"📤 Enviando ao Prompt Manager: {k['palavra']} (score: {k['score_final']})")
    # Aqui entraria a integração real com API REST ou banco intermediário

# =============================
# EXPORTAÇÃO JSON/CSV
# =============================
def exportar_resultados(validadas: list[dict], reprovadas: list[str], trace_id: str):
    with open(EXPORT_DIR / f"validadas_{trace_id}.json", "w", encoding="utf-8") as f:
        json.dump(validadas, f, ensure_ascii=False, indent=2)
    with open(EXPORT_DIR / f"reprovadas_{trace_id}.json", "w", encoding="utf-8") as f:
        json.dump(reprovadas, f, ensure_ascii=False, indent=2)

# =============================
# EXECUÇÃO DO PIPELINE
# =============================
def executar_pipeline_validador(dry_run: bool = False):
    trace_id = str(uuid.uuid4())
    logger.info(f"▶️ Início da execução do pipeline | trace_id={trace_id}")
    inicio = time.time()

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        palavras = carregar_palavras(session)
        validadas = validar_keywords_com_google_planner(
            palavras,
            trace_id=trace_id,
            volume_min=100,
            score_min=1000,
            modo="mock"
        )

        # Aplica filtros adicionais
        aprovadas = filtrar_keywords(
            validadas,
            concorrencia_aceita=["baixa", "média"],
            palavras_excluidas=["grátis", "clique aqui"],
            volume_min=1000,
            score_min=1000
        )

        palavras_validadas = set(k['palavra'] for k in aprovadas)
        reprovadas = [p for p in palavras if p not in palavras_validadas]

        for resultado in aprovadas:
            if not dry_run:
                atualizar_palavra(session, resultado, trace_id)

        if not dry_run:
            session.commit()
            enviar_ao_prompt_manager(aprovadas)

        exportar_resultados(aprovadas, reprovadas, trace_id)

        duracao = round(time.time() - inicio, 2)
        logger.info(json.dumps({
            "trace_id": trace_id,
            "total_lidas": len(palavras),
            "validadas": len(aprovadas),
            "reprovadas": len(reprovadas),
            "exportadas": len(aprovadas),
            "tempo_execucao": f"{duracao}s"
        }, indent=2))

    except Exception as e:
        logger.error(f"❌ Erro no pipeline: {e}")
        session.rollback()
    finally:
        session.close()
        logger.info(f"✅ Pipeline encerrado | trace_id={trace_id}")

# =============================
# MAIN
# =============================
if __name__ == "__main__":
    executar_pipeline_validador(dry_run=False)
