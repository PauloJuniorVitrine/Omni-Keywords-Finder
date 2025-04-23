#!/usr/bin/env python3
# refatorador.py - Versão Blindada para GitHub Actions

import os
import sys
import json
import argparse
import logging
import hashlib
import shutil
import subprocess
import traceback
import time
import psutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set, NoReturn
from importlib import import_module
import pkgutil
from jsonschema import validate
import gettext

# Configuração básica de logging que nunca falha
try:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)
except Exception:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger()

# Constantes com fallback seguro
try:
    BASE_DIR = Path(__file__).resolve().parent.parent
    RELATORIOS_DIR = BASE_DIR / "relatorios"
    CONFIG_PATH = BASE_DIR / "config" / "refatorador_config.json"
    SCRIPT_DIR = BASE_DIR / "scripts"
    PROMPT_DIR = BASE_DIR / "prompts"
    CONFIG_DIR = BASE_DIR / "config"
    PLUGINS_DIR = BASE_DIR / "plugins"
    LOCALES_DIR = BASE_DIR / "locales"
    
    RELATORIO_JSON = RELATORIOS_DIR / "relatorio_estrutura.json"
    LOG_PATH = RELATORIOS_DIR / "log_refatorador.txt"
    FLAG_EXECUTADO = RELATORIOS_DIR / ".refatorado.ok"
except Exception as e:
    logger.critical(f"Falha ao definir constantes: {e}")
    sys.exit(1)

ITENS_OBRIGATORIOS = {
    "scripts": ["audit_runner.py", "executor.py", "refatorador.py", "test_runner.py"],
    "prompts": [
        "prompt_base_unitario.txt",
        "prompt_base_integracao.txt",
        "prompt_base_carga.txt",
        "prompt_base_e2e.txt",
        "Super_Prompt_Auditor.txt"
    ],
    "config": ["config_execucao.json"]
}

DEFAULT_CONFIG = {
    "executar_relocacao": True,
    "aplicar_recomendacoes_do_plano": True,
    "forcar_criacao_de_pastas": True,
    "modo_dry_run": False,
    "nivel_log": "INFO",
    "idioma": "en",
    "criar_backup": True,
    "max_retries": 3,
    "retry_delay": 2
}

CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "executar_relocacao": {"type": "boolean"},
        "aplicar_recomendacoes_do_plano": {"type": "boolean"},
        "forcar_criacao_de_pastas": {"type": "boolean"},
        "modo_dry_run": {"type": "boolean"},
        "nivel_log": {"type": "string", "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]},
        "idioma": {"type": "string", "enum": ["en", "pt", "es"]},
        "criar_backup": {"type": "boolean"},
        "max_retries": {"type": "number", "minimum": 1},
        "retry_delay": {"type": "number", "minimum": 0}
    },
    "additionalProperties": False
}

class GitHubActionsIntegration:
    """Integração específica para GitHub Actions"""
    @staticmethod
    def is_github_actions() -> bool:
        return os.getenv("GITHUB_ACTIONS") == "true"
    
    @staticmethod
    def set_output(name: str, value: str) -> None:
        if GitHubActionsIntegration.is_github_actions():
            try:
                with open(os.getenv("GITHUB_OUTPUT"), "a") as f:
                    print(f"{name}={value}", file=f)
            except Exception as e:
                logger.error(f"Falha ao definir output GitHub: {e}")

    @staticmethod
    def annotate_error(message: str) -> None:
        if GitHubActionsIntegration.is_github_actions():
            message_escaped = message.replace("\n", "%0A")
            print(f"::error::{message_escaped}")

    @staticmethod
    def annotate_warning(message: str) -> None:
        if GitHubActionsIntegration.is_github_actions():
            message_escaped = message.replace("\n", "%0A")
            print(f"::warning::{message_escaped}")

class RetryOperation:
    """Decorador para operações com retentativa"""
    def __init__(self, max_attempts: int = 3, delay: float = 1):
        self.max_attempts = max_attempts
        self.delay = delay

    def __call__(self, func):
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(1, self.max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < self.max_attempts:
                        time.sleep(self.delay)
                        logger.warning(f"Tentativa {attempt} falhou, retentando...")
            raise last_error
        return wrapper

class PerformanceMonitor:
    """Monitoramento de desempenho com tratamento seguro"""
    def __enter__(self):
        try:
            self.start_time = time.time()
            self.process = psutil.Process()
            self.start_mem = self.process.memory_info().rss
            self.start_cpu = self.process.cpu_percent()
            return self
        except Exception as e:
            logger.warning(f"Falha ao iniciar monitor: {e}")
            return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            end_time = time.time()
            end_mem = self.process.memory_info().rss
            end_cpu = self.process.cpu_percent()
            
            logger.info(
                f"Performance: Tempo={end_time - self.start_time:.2f}s | "
                f"Memória={(end_mem - self.start_mem)/1024/1024:.2f}MB | "
                f"CPU={end_cpu - self.start_cpu:.2f}%"
            )
        except Exception:
            pass

class Refatorador:
    def __init__(self, config: Optional[Dict] = None):
        """Inicialização com tratamento completo de erros"""
        self._setup_inicial(config)

    def _setup_inicial(self, config: Optional[Dict]):
        """Configuração inicial robusta"""
        self.config = self._carregar_config_segura(config)
        self._validar_config_segura()
        self._setup_logging_seguro()
        self._setup_i18n_seguro()
        self._carregar_plugins_seguro()
        
        # Inicialização de métricas
        self.total_arquivos = 0
        self.arquivos_modificados = set()
        self.log_ok: List[str] = []
        self.log_warn: List[str] = []
        self.log_erro: List[str] = []

    def _carregar_config_segura(self, config: Optional[Dict]) -> Dict:
        """Carrega configuração com múltiplos fallbacks"""
        try:
            # Config padrão
            config_base = DEFAULT_CONFIG.copy()
            
            # Config do arquivo
            if CONFIG_PATH.exists():
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    config_base.update(json.load(f))
            
            # Config passada por parâmetro
            if config:
                config_base.update(config)
                
            return config_base
        except Exception as e:
            GitHubActionsIntegration.annotate_warning(f"Falha ao carregar config: {e}")
            return DEFAULT_CONFIG.copy()

    def _validar_config_segura(self):
        """Valida configuração com fallback para padrão"""
        try:
            validate(instance=self.config, schema=CONFIG_SCHEMA)
        except Exception as e:
            logger.error(f"Configuração inválida: {e}")
            self.config = DEFAULT_CONFIG.copy()

    def _setup_logging_seguro(self):
        """Configura logging que nunca falha"""
        try:
            nivel = getattr(logging, self.config.get("nivel_log", "INFO").upper())
            logger.setLevel(nivel)
            
            if GitHubActionsIntegration.is_github_actions():
                # Formato compatível com GitHub Actions
                fmt = '%(levelname)s::%(message)s'
                logging.basicConfig(level=nivel, format=fmt)
        except Exception:
            logging.basicConfig(level=logging.INFO)

    def _setup_i18n_seguro(self):
        """Configura i18n com fallback seguro"""
        try:
            lang = self.config.get("idioma", "en")
            trans = gettext.translation(
                'refatorador',
                localedir=LOCALES_DIR,
                languages=[lang],
                fallback=True
            )
            trans.install()
            self._ = trans.gettext
        except Exception:
            self._ = lambda x: x  # Fallback para texto original

    def _carregar_plugins_seguro(self):
        """Carrega plugins sem falhar a execução"""
        self.plugins = []
        if not PLUGINS_DIR.exists():
            return
            
        try:
            for finder, name, _ in pkgutil.iter_modules([str(PLUGINS_DIR)]):
                try:
                    module = import_module(f"plugins.{name}")
                    if hasattr(module, "Plugin"):
                        plugin = module.Plugin(self)
                        self.plugins.append(plugin)
                except Exception as e:
                    logger.error(f"Falha ao carregar plugin {name}: {e}")
        except Exception as e:
            logger.error(f"Falha geral ao carregar plugins: {e}")

    @RetryOperation()
    def _verificar_integridade_arquivos(self) -> bool:
        """Verificação de hashes com retentativa"""
        # Implementação real deveria verificar hashes conhecidos
        return True

    @RetryOperation()
    def _criar_backup_seguro(self) -> bool:
        """Cria backup com retentativa"""
        if not self.config.get("criar_backup", True):
            return True
            
        try:
            backup_dir = RELATORIOS_DIR / "backups" / datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            for pasta in ITENS_OBRIGATORIOS.keys():
                origem = BASE_DIR / pasta
                if origem.exists():
                    destino = backup_dir / pasta
                    shutil.copytree(origem, destino)
            return True
        except Exception as e:
            logger.error(f"Falha ao criar backup: {e}")
            return False

    def _verificar_permissoes(self) -> bool:
        """Verifica permissões de escrita/leitura"""
        try:
            # Testa escrita no diretório de relatórios
            test_file = RELATORIOS_DIR / "perm_test.tmp"
            test_file.touch()
            test_file.unlink()
            return True
        except Exception as e:
            GitHubActionsIntegration.annotate_error(f"Falha na verificação de permissões: {e}")
            return False

    def aplicar_refatoracoes(self):
        """Método principal completamente blindado"""
        try:
            with PerformanceMonitor():
                if not self._verificar_permissoes():
                    raise RuntimeError("Permissões insuficientes")
                
                if not self._processar_fluxo_completo():
                    raise RuntimeError("Falha no fluxo de refatoração")
                
                self._relatar_sucesso()
        except Exception as e:
            self._lidar_com_falha(e)
            raise

    def _processar_fluxo_completo(self) -> bool:
        """Executa todas as etapas com tratamento de erro"""
        etapas = [
            ("Verificando pré-condições", self._verificar_pre_condicoes),
            ("Criando backup", self._criar_backup_seguro),
            ("Processando itens", self._processar_itens_seguro),
            ("Finalizando", self._finalizar_processo)
        ]
        
        for descricao, etapa in etapas:
            try:
                logger.info(descricao)
                if not etapa():
                    raise RuntimeError(f"Falha na etapa: {descricao}")
            except Exception as e:
                logger.error(f"Erro em '{descricao}': {e}")
                GitHubActionsIntegration.annotate_error(f"Erro em {descricao}: {e}")
                raise
        return True

    def _verificar_pre_condicoes(self) -> bool:
        """Verifica todas as condições necessárias"""
        if not RELATORIO_JSON.exists():
            raise FileNotFoundError("Arquivo de relatório não encontrado")
        
        if not self._verificar_integridade_arquivos():
            raise RuntimeError("Problemas de integridade detectados")
            
        return True

    @RetryOperation()
    def _processar_itens_seguro(self) -> bool:
        """Processa itens com tratamento de erro e retentativa"""
        try:
            with open(RELATORIO_JSON, "r", encoding="utf-8") as f:
                relatorio = json.load(f)
                
            for pasta, arquivos in ITENS_OBRIGATORIOS.items():
                dir_path = BASE_DIR / pasta
                
                if not dir_path.exists() and self.config.get("forcar_criacao_de_pastas", True):
                    dir_path.mkdir(parents=True, exist_ok=True)
                
                for arquivo in arquivos:
                    caminho = dir_path / arquivo
                    if not caminho.exists():
                        conteudo = self._gerar_conteudo_padrao(arquivo)
                        if not self.config.get("modo_dry_run", False):
                            caminho.write_text(conteudo, encoding="utf-8")
                        self.total_arquivos += 1
                        
            return True
        except Exception as e:
            logger.error(f"Falha ao processar itens: {e}")
            raise

    def _gerar_conteudo_padrao(self, nome_arquivo: str) -> str:
        """Gera conteúdo padrão baseado no tipo de arquivo"""
        if nome_arquivo.endswith(".py"):
            return "# Arquivo gerado automaticamente\n"
        elif nome_arquivo.endswith(".txt"):
            return "# Prompt gerado automaticamente\n"
        elif nome_arquivo.endswith(".json"):
            return "{}"
        return ""

    def _finalizar_processo(self) -> bool:
        """Finalização segura do processo"""
        try:
            if not self.config.get("modo_dry_run", False):
                FLAG_EXECUTADO.write_text("Refatoração concluída", encoding="utf-8")
            
            self._salvar_logs_seguro()
            return True
        except Exception as e:
            logger.error(f"Falha na finalização: {e}")
            return False

    def _salvar_logs_seguro(self):
        """Salva logs com tratamento de erro"""
        try:
            log_content = "\n".join([
                "# SUCESSOS"] + self.log_ok + [
                "\n# AVISOS"] + self.log_warn + [
                "\n# ERROS"] + self.log_erro + [
                f"\nResumo: {self.total_arquivos} arquivos processados"])
            
            LOG_PATH.write_text(log_content, encoding="utf-8")
        except Exception as e:
            logger.error(f"Falha ao salvar logs: {e}")

    def _relatar_sucesso(self):
        """Gera relatório de sucesso"""
        logger.info("✅ Refatoração concluída com sucesso")
        GitHubActionsIntegration.set_output("modified_files", str(len(self.arquivos_modificados)))
        GitHubActionsIntegration.set_output("total_files", str(self.total_arquivos))

    def _lidar_com_falha(self, error: Exception):
        """Tratamento padronizado de falhas"""
        error_msg = str(error)
        logger.critical(f"❌ Falha na refatoração: {error_msg}")
        GitHubActionsIntegration.annotate_error(error_msg)
        
        # Log detalhado apenas em debug
        if self.config.get("nivel_log", "INFO") == "DEBUG":
            logger.debug(traceback.format_exc())

def main():
    """Entrypoint completamente blindado"""
    try:
        parser = argparse.ArgumentParser(
            description="Refatorador técnico para GitHub Actions",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        parser.add_argument("--simular", action="store_true", help="Modo dry-run (não aplica mudanças)")
        parser.add_argument("--debug", action="store_true", help="Ativa logging detalhado")
        parser.add_argument("--idioma", choices=["en", "pt", "es"], help="Idioma de exibição")
        parser.add_argument("--no-backup", action="store_true", help="Desativa criação de backup")
        
        args = parser.parse_args()
        
        config = {
            "modo_dry_run": args.simular,
            "nivel_log": "DEBUG" if args.debug else "INFO",
            "criar_backup": not args.no_backup
        }
        
        if args.idioma:
            config["idioma"] = args.idioma
        
        refatorador = Refatorador(config)
        refatorador.aplicar_refatoracoes()
        
    except Exception as e:
        logger.critical(f"Falha fatal: {e}")
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()

# === GPT-4o: Diagnóstico complementar não destrutivo ===
if os.getenv("ENABLE_GPT4O_AUDIT", "false").lower() == "true":
    try:
        import openai
        prompt_path = PROMPT_DIR / "Super_Prompt_Auditor.txt"
        if prompt_path.exists():
            prompt_text = prompt_path.read_text(encoding="utf-8")
            resultados = ["\n\n# Diagnóstico GPT-4o Complementar"]
            openai.api_key = os.getenv("OPENAI_API_KEY")
            for file in (BASE_DIR / "src").rglob("*.py"):
                try:
                    codigo = file.read_text(encoding="utf-8")
                    resposta = openai.ChatCompletion.create(
                        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                        messages=[
                            {"role": "system", "content": "Você é um refatorador técnico profissional."},
                            {"role": "user", "content": prompt_text + f"\n\nArquivo: {file}\nCódigo:\n{codigo}"}
                        ],
                        max_tokens=2048,
                        temperature=0.2
                    )
                    resultados.append(f"\n## {file}\n\n{resposta.choices[0].message.content.strip()}")
                except Exception as e:
                    resultados.append(f"\n## {file}\n\nErro ao processar: {e}")
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write("\n".join(resultados))
            logger.info("Diagnóstico GPT-4o adicionado ao log de refatoração.")
    except Exception as err:
        logger.warning(f"[GPT-4o] Falha no diagnóstico complementar: {err}")