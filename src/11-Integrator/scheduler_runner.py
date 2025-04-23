import schedule
import time
import logging
from config_loader import load_config
from system_integrator import iniciar_integracao

# ─────────────────────────────────────────────────────────────
# Carregar configuração
# ─────────────────────────────────────────────────────────────
CONFIG = load_config("config.v2.json", "config_schema.v2.json")
log_level = CONFIG.get("logging", {}).get("global_level", "INFO")

logging.basicConfig(
    level=getattr(logging, log_level),
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ─────────────────────────────────────────────────────────────
# Agendamento por módulo via config
# ─────────────────────────────────────────────────────────────
def agendar_pipelines(nicho_default: str = "marketing"):
    scheduler_cfg = CONFIG.get("scheduler", {}).get("modules", {})
    
    for nome_modulo, horario in scheduler_cfg.items():
        logging.info(f"📅 Agendando módulo '{nome_modulo}' para {horario}...")
        schedule.every().day.at(horario).do(lambda: iniciar_integracao(nicho_default, dry_run=False))

    while True:
        schedule.run_pending()
        time.sleep(60)

# ─────────────────────────────────────────────────────────────
# Execução
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.info("🔁 Iniciando Scheduler Runner do Omni Integrator...")
    agendar_pipelines()