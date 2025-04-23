import os
import logging
import argparse
import json
from datetime import datetime
from utils.date_helper import obter_nome_semana
from utils.trace_helper import gerar_trace_id
from exporter.exportar_zip_pronto import exportar_zip  # Integração automática com zipador

# =====================
# CONFIGURAÇÕES
# =====================
ZIP_DIR = "exports/zips"
ENVIO_DESTINO = os.getenv("EXPORTADOR_DESTINO", "INTEGRADOR_DEMANDA")

# =====================
# LOGGING E TRACE ID
# =====================
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("exportador")

def obter_caminhos_zip():
    zip_name = obter_nome_semana()
    zip_path = os.path.join(ZIP_DIR, zip_name)
    sha256_path = zip_path + ".sha256"
    lock_path = os.path.join(ZIP_DIR, f".lock_{zip_name}")
    return zip_name, zip_path, sha256_path, lock_path

def exportar_zip(dry_run=False, trace_id=None):
    """
    Exporta o arquivo ZIP semanal gerado para um sistema externo (placeholder).

    Parâmetros:
        dry_run (bool): Se True, apenas simula a exportação sem executar envio real.
        trace_id (str): Opcional. Trace ID herdado do zipador, se houver.

    Exemplo:
        $ python exportar_zip_pronto.py --dry-run

    Observação:
        Agora que essa função suporta integração automática com o zipador, 
        lembre-se de garantir que o PromptZipService chame essa função ao final da execução com o mesmo trace_id.
    """
    trace_id = trace_id or gerar_trace_id()
    zip_name, zip_path, sha256_path, lock_path = obter_caminhos_zip()

    if not os.path.exists(zip_path):
        logger.warning(f"[TRACE_ID={trace_id}] Arquivo ZIP não encontrado: {zip_path}")
        return

    if not os.path.exists(sha256_path):
        logger.warning(f"[TRACE_ID={trace_id}] Checksum SHA256 não encontrado: {sha256_path}")
        return

    if not os.path.exists(lock_path):
        logger.warning(f"[TRACE_ID={trace_id}] Lock da semana não encontrado: {lock_path}. Exportação abortada.")
        return

    logger.info(f"[TRACE_ID={trace_id}] Iniciando exportação do arquivo: {zip_path}")

    with open(sha256_path, "r") as f:
        checksum = f.read().strip()
        logger.info(f"[TRACE_ID={trace_id}] SHA256 do arquivo: {checksum}")

    if dry_run:
        logger.info("[DRY-RUN] Simulando envio do ZIP. Nenhum dado será transferido.")
        return

    try:
        logger.info(f"[TRACE_ID={trace_id}] Enviando {zip_name} para destino: {ENVIO_DESTINO}")
        # Aqui será feita a integração real no futuro (ex: requests.post, boto3, etc.)

        logger.info(json.dumps({
            "trace_id": trace_id,
            "acao": "exportar_zip",
            "arquivo": zip_name,
            "sha256": checksum,
            "destino": ENVIO_DESTINO,
            "status": "simulado"
        }))

        logger.info(f"[TRACE_ID={trace_id}] Exportação simulada concluída com sucesso.")
    except Exception as e:
        logger.error(f"[TRACE_ID={trace_id}] Falha ao exportar arquivo: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='Executa em modo simulação (nenhum envio real)')
    args = parser.parse_args()
    exportar_zip(dry_run=args.dry_run)

# Integração automática com zipador (exemplo de uso no PromptZipService):
# from exporter.exportar_zip_pronto import exportar_zip
# exportar_zip(trace_id=self.trace_id)
