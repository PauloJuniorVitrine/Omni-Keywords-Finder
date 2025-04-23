# theme_manager/scheduler/cron_jobs.py

import datetime
import logging
import uuid
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_
from theme_manager.database import engine
from theme_manager.models.categoria import Categoria
from theme_manager.models.tema import Tema
from theme_manager.models.nicho import Nicho
from theme_manager.scheduler.agendador import simular_coleta

# Logger configurado
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

LOG_EXECUCOES_PATH = "logs/log_execucoes.json"

def get_data_hora_atual():
    agora = datetime.datetime.now()
    return agora.date(), agora.time(), agora.strftime('%A').lower()

def gerar_trace_id():
    return str(uuid.uuid4())

def registrar_execucao(trace_id, categoria, status, duracao_ms=None, nivel="INFO", erro=None):
    log_data = {
        "timestamp": datetime.datetime.now().isoformat(),
        "trace_id": trace_id,
        "level": nivel,
        "evento": "execucao_categoria",
        "nicho": categoria.tema.nicho.nome,
        "tema": categoria.tema.descricao,
        "categoria": categoria.descricao,
        "status": status,
        "duracao_ms": duracao_ms,
        "erro": str(erro) if erro else None
    }
    try:
        with open(LOG_EXECUCOES_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_data) + "\n")
    except Exception as e:
        logger.warning(f"[⚠️] Falha ao registrar log estruturado: {e}")

def executar_categoria(categoria, trace_id, dry_run=False):
    inicio = datetime.datetime.now()
    try:
        tema = categoria.tema
        nicho = tema.nicho

        if dry_run:
            logger.info(f"[DRY-RUN] Simulação para: Nicho='{nicho.nome}', Tema='{tema.descricao}', Categoria='{categoria.descricao}'")
        else:
            simular_coleta(nicho.nome, tema.descricao, categoria.descricao)
            logger.info(f"[✔️] Coleta executada: Nicho='{nicho.nome}' | Tema='{tema.descricao}' | Categoria='{categoria.descricao}'")

        # Verifica se hoje é o último dia da coleta
        if categoria.data_entrega_resultado == datetime.date.today():
            categoria.ativo = False
            logger.info(f"[🔒] Ciclo encerrado automaticamente para categoria '{categoria.descricao}'.")

        duracao = (datetime.datetime.now() - inicio).total_seconds() * 1000
        registrar_execucao(trace_id, categoria, status="executado", duracao_ms=duracao)

    except Exception as e:
        duracao = (datetime.datetime.now() - inicio).total_seconds() * 1000
        logger.error(f"[❌] Erro ao executar categoria '{categoria.descricao}': {e}", exc_info=True)
        registrar_execucao(trace_id, categoria, status="erro", duracao_ms=duracao, nivel="ERROR", erro=e)

def executar_cron(verbose: bool = True, dry_run: bool = False):
    trace_id = gerar_trace_id()
    data_hoje, hora_agora, dia_semana = get_data_hora_atual()

    if verbose:
        logger.info(f"📆 {data_hoje} ({dia_semana}) — Cron iniciado às {hora_agora.strftime('%H:%M')} — Trace ID: {trace_id}")

    try:
        with Session(engine) as session:
            categorias = (
                session.query(Categoria)
                .options(joinedload(Categoria.tema).joinedload(Tema.nicho))
                .filter(
                    Categoria.ativo == True,
                    Categoria.data_inicio_coleta <= data_hoje,
                    Categoria.data_entrega_resultado >= data_hoje,
                    Categoria.dia_semana == dia_semana,
                    Categoria.hora_execucao <= hora_agora
                )
                .all()
            )

            if not categorias:
                if verbose:
                    logger.info("[ℹ️] Nenhuma categoria ativa ou elegível para execução neste momento.")
                return

            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(executar_categoria, categoria, trace_id, dry_run) for categoria in categorias]
                for future in as_completed(futures):
                    future.result()  # força o lançamento de exceções, se houver

            session.commit()

    except Exception as e:
        logger.error(f"[ERRO] Falha geral no cronjob: {e}", exc_info=True)
