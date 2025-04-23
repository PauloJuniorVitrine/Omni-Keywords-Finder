import logging
import asyncio
import schedule
import time
from typing import List, Protocol
from prometheus_client import Counter, Histogram, start_http_server

from config_loader import load_config
from src.modules.2_colector.google_autocomplete import GoogleAutocompleteCollector
from src.modules.2_colector.google_trends import GoogleTrendsCollector
from src.modules.3_processing.processing import KeywordProcessor
from src.modules.1_data_base.queries import inserir_multiplas_palavras
from src.modules.4_api.send_to_api import APIClient

# ─────────────────────────────────────────────────────────────
# 🔧 Carregamento de Configuração
# ─────────────────────────────────────────────────────────────
CONFIG = load_config("config.v2.json", "config_schema.v2.json")

# ─────────────────────────────────────────────────────────────
# 📊 MÉTRICAS (Prometheus)
# ─────────────────────────────────────────────────────────────
PALAVRAS_PROCESSADAS = Counter("palavras_processadas_total", "Total de palavras processadas")
TEMPO_EXECUCAO_PIPELINE = Histogram("tempo_execucao_pipeline_segundos", "Tempo de execução do pipeline")
start_http_server(CONFIG.get("metrics", {}).get("port", 8000))

# ─────────────────────────────────────────────────────────────
# ⚙️ LOGGING
# ─────────────────────────────────────────────────────────────
log_cfg = CONFIG.get("logging", {})
log_level = getattr(logging, log_cfg.get("global_level", "INFO"))
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/integrator.log"),
        logging.StreamHandler()
    ]
)

# ─────────────────────────────────────────────────────────────
# 🧩 INTERFACE DE COLETORES
# ─────────────────────────────────────────────────────────────
class ColetorBase(Protocol):
    def coletar(self, nicho: str) -> List[str]: ...

class SystemIntegrator:
    def __init__(self, nicho: str, dry_run: bool = False):
        self.nicho = nicho
        self.dry_run = dry_run
        self.processor = KeywordProcessor()
        self.api_client = APIClient()
        self.coletores: List[ColetorBase] = [
            GoogleAutocompleteCollector(),
            GoogleTrendsCollector(),
        ]
        self.timeout_coleta = CONFIG["timeout"]
        self.timeout_processamento = 20
        self.timeout_storage = 10

    async def coletar_dados(self) -> List[str]:
        tasks = [asyncio.to_thread(c.coletar, self.nicho) for c in self.coletores]
        resultados = await asyncio.gather(*tasks, return_exceptions=True)
        palavras = []
        for result, coletor in zip(resultados, self.coletores):
            if isinstance(result, Exception):
                logging.error(f"❌ Erro em coletor {coletor.__class__.__name__}: {result}")
            else:
                palavras += result
        palavras = list(set(palavras))
        logging.info(f"📊 Total de palavras coletadas: {len(palavras)}")
        return palavras

    async def processar_dados(self, palavras: List[str]) -> List[str]:
        try:
            processadas = self.processor.processar_palavras(palavras)
            logging.info(f"🔍 {len(processadas)} palavras após processamento.")
            PALAVRAS_PROCESSADAS.inc(len(processadas))
            return processadas
        except Exception as e:
            logging.exception(f"❌ Erro ao processar palavras: {e}")
            return []

    async def armazenar_dados(self, palavras: List[str]):
        if self.dry_run:
            logging.info("🧪 [Dry-Run] Armazenamento simulado.")
            return
        try:
            if palavras:
                await inserir_multiplas_palavras(self.nicho, palavras)
                logging.info(f"💾 {len(palavras)} palavras armazenadas no banco.")
            else:
                logging.warning("⚠️ Nenhuma palavra para armazenar.")
        except Exception as e:
            logging.exception(f"❌ Erro ao armazenar no banco: {e}")

    async def enviar_para_api(self, palavras: List[str]):
        if self.dry_run:
            logging.info("🧪 [Dry-Run] Envio para API simulado.")
            return
        try:
            if palavras:
                await self.api_client.enviar_para_api(self.nicho, palavras)
            else:
                logging.warning("⚠️ Nenhuma palavra para enviar à API.")
        except Exception as e:
            logging.exception(f"❌ Erro ao enviar para API: {e}")

    @TEMPO_EXECUCAO_PIPELINE.time()
    async def executar_pipeline(self):
        logging.info(f"🚀 Iniciando pipeline para o nicho '{self.nicho}' (dry_run={self.dry_run})")
        try:
            palavras = await asyncio.wait_for(self.coletar_dados(), timeout=self.timeout_coleta)
            palavras_processadas = await asyncio.wait_for(self.processar_dados(palavras), timeout=self.timeout_processamento)
            await asyncio.wait_for(self.armazenar_dados(palavras_processadas), timeout=self.timeout_storage)
            await asyncio.wait_for(self.enviar_para_api(palavras_processadas), timeout=self.timeout_storage)
            logging.info("✅ Integração concluída com sucesso.")
        except asyncio.TimeoutError:
            logging.error("⏱️ Pipeline cancelado por tempo excedido.")
        except Exception as e:
            logging.exception(f"❌ Erro inesperado no pipeline: {e}")