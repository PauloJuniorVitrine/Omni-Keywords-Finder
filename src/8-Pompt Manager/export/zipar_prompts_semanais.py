import os
import json
import shutil
import logging
import zipfile
import calendar
import hashlib
import argparse
from datetime import datetime, timedelta
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from template_manager.templates.models.prompt_gerado_model import PromptGerado
from slugify import slugify
import uuid
import requests
from exporter.exportar_zip_pronto import exportar_zip  # Integração com exportador

# =====================
# CONFIGURAÇÕES
# =====================
OUTPUT_DIR = "exports/prompts_temp"
ZIP_DIR = "exports/zips"
DB_URL = os.getenv("DATABASE_URL", "sqlite:///db.sqlite3")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")

# =====================
# LOGGING E TRACE ID
# =====================
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger("zipador")

def gerar_trace_id():
    return str(uuid.uuid4())

def gerar_checksum(path):
    sha256 = hashlib.sha256()
    with open(path, 'rb') as f:
        for bloco in iter(lambda: f.read(4096), b''):
            sha256.update(bloco)
    return sha256.hexdigest()

def obter_intervalo_da_semana():
    hoje = datetime.now()
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    fim_semana = inicio_semana + timedelta(days=6)
    return inicio_semana.replace(hour=0, minute=0, second=0), fim_semana.replace(hour=23, minute=59, second=59)

def obter_nome_semana():
    hoje = datetime.now()
    numero_semana = hoje.isocalendar()[1]
    ano = hoje.year
    return f"prompts_semana_{numero_semana}_{ano}.zip"

class PromptZipService:
    def __init__(self, db_url=DB_URL, dry_run=False):
        self.db_url = db_url
        self.trace_id = gerar_trace_id()
        self.engine = create_engine(self.db_url)
        self.Session = sessionmaker(bind=self.engine)
        self.inicio_semana, self.fim_semana = obter_intervalo_da_semana()
        self.dry_run = dry_run
        self.zip_name = obter_nome_semana()
        self.lock_path = os.path.join(ZIP_DIR, f".lock_{self.zip_name}")

    def executar(self):
        if os.path.exists(self.lock_path):
            logger.info("⚠️ ZIP dessa semana já foi gerado anteriormente. Abortando...")
            return

        if self.dry_run:
            logger.info("🧪 Modo DRY-RUN ativado. Nenhum arquivo será salvo ou zipado.")

        logger.info(f"[TRACE_ID={self.trace_id}] Iniciando extração de prompts de {self.inicio_semana.date()} a {self.fim_semana.date()}")
        session = self.Session()
        try:
            prompts = session.query(PromptGerado).filter(PromptGerado.criado_em.between(self.inicio_semana, self.fim_semana)).all()
        except Exception as e:
            logger.error(f"Erro ao acessar o banco de dados: {e}")
            return
        finally:
            session.close()

        if not prompts:
            logger.warning("Nenhum prompt encontrado para a semana atual.")
            return

        if os.path.exists(OUTPUT_DIR):
            shutil.rmtree(OUTPUT_DIR)
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        metricas = {
            "total_prompts": len(prompts),
            "nichos": set(),
            "categorias": set(),
            "data_inicio": self.inicio_semana.isoformat(),
            "data_fim": self.fim_semana.isoformat(),
        }

        for prompt in prompts:
            try:
                pasta_destino = os.path.join(OUTPUT_DIR, prompt.nicho, prompt.categoria.value)
                os.makedirs(pasta_destino, exist_ok=True)
                metricas["nichos"].add(prompt.nicho)
                metricas["categorias"].add(prompt.categoria.value)

                prompt_dict = {
                    "palavra_chave": prompt.palavra_chave,
                    "palavra_secundaria": prompt.palavra_secundaria,
                    "conteudo": prompt.texto_gerado,
                    "trace_id": self.trace_id,
                    "criado_em": prompt.criado_em.isoformat()
                }

                file_base = slugify(prompt.palavra_chave)
                json_path = os.path.join(pasta_destino, f"{file_base}.json")
                txt_path = os.path.join(pasta_destino, f"{file_base}.txt")

                if not self.dry_run:
                    with open(json_path, "w", encoding="utf-8") as f:
                        json.dump(prompt_dict, f, ensure_ascii=False, indent=2)
                    with open(txt_path, "w", encoding="utf-8") as f:
                        f.write(prompt.texto_gerado)

            except Exception as e:
                logger.error(f"Erro ao processar prompt '{prompt.palavra_chave}': {e}")

        metricas["nichos"] = len(metricas["nichos"])
        metricas["categorias"] = len(metricas["categorias"])

        if not self.dry_run:
            os.makedirs(ZIP_DIR, exist_ok=True)
            zip_path = os.path.join(ZIP_DIR, self.zip_name)

            try:
                shutil.make_archive(zip_path.replace(".zip", ""), 'zip', OUTPUT_DIR)
                checksum = gerar_checksum(zip_path)
                with open(zip_path + ".sha256", "w") as f:
                    f.write(checksum)

                with open(os.path.join(ZIP_DIR, "metrics.json"), "w") as f:
                    json.dump(metricas, f, indent=2)

                with open(self.lock_path, "w") as f:
                    f.write(datetime.now().isoformat())

                logger.info(f"[TRACE_ID={self.trace_id}] ZIP gerado com sucesso: {zip_path}")

                if WEBHOOK_URL:
                    try:
                        requests.post(WEBHOOK_URL, json={"status": "ok", "arquivo": zip_path})
                    except Exception as e:
                        logger.warning(f"Falha ao notificar webhook: {e}")

                # 🚀 Chamada automática do exportador com o mesmo trace_id
                exportar_zip(trace_id=self.trace_id)

            except Exception as e:
                logger.error(f"Erro ao criar arquivo ZIP: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    zipador = PromptZipService(dry_run=args.dry_run)
    zipador.executar()
