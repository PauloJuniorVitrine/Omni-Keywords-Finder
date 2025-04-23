#!/usr/bin/env python3
# executor.py - Versão Blindada para GitHub Actions

import json
import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, NoReturn
import traceback

class GitHubActionsShield:
    """Proteções específicas para GitHub Actions"""
    
    @staticmethod
    def verify_environment():
        """Verifica variáveis críticas do GitHub"""
        required_vars = [
            'GITHUB_WORKSPACE',
            'GITHUB_REPOSITORY',
            'GITHUB_ACTIONS'
        ]
        missing = [var for var in required_vars if not os.getenv(var)]
        if missing:
            raise RuntimeError(f"Variáveis GitHub faltando: {', '.join(missing)}")

    @staticmethod
    def safe_path(path: str) -> Path:
        """Garante que o path está contido no workspace"""
        workspace = Path(os.getenv('GITHUB_WORKSPACE', '.'))
        full_path = (workspace / path).resolve()
        
        if not str(full_path).startswith(str(workspace)):
            raise SecurityError(f"Tentativa de acesso a path fora do workspace: {path}")
        return full_path

    @staticmethod
    def annotate_error(message: str, file: str = None, line: str = None):
        """Cria anotações de erro no formato GitHub"""
        if GitHubActionsShield.is_github():
            loc = f" file={file},line={line}" if file and line else ""
            print(f"::error{loc}::{message.replace('\n', '%0A')}")

    @staticmethod
    def is_github() -> bool:
        """Verifica se está executando no GitHub Actions"""
        return os.getenv('GITHUB_ACTIONS') == 'true'

class SecurityError(Exception):
    """Erro de violação de segurança"""
    pass

class PipelineExecutor:
    """Executor blindado para GitHub Actions"""
    
    def __init__(self):
        self._setup_emergency_handlers()
        self._setup_logging()
        self._verify_environment()
        self._load_config()
        self._setup_paths()
        
        # Configuração de segurança
        self.timeout = 300
        self.max_retries = 3
        self.safe_commands = ['python', 'pytest', 'audit_runner.py']
        
    def _setup_emergency_handlers(self):
        """Configura tratadores para sinais de sistema"""
        signal.signal(signal.SIGTERM, self._emergency_shutdown)
        signal.signal(signal.SIGINT, self._emergency_shutdown)
        signal.signal(signal.SIGQUIT, self._emergency_shutdown)

    def _emergency_shutdown(self, signum, frame) -> NoReturn:
        """Encerramento seguro em caso de falha crítica"""
        logging.critical(f"🚨 SHUTDOWN EMERGENCIAL (sinal {signum})")
        self._generate_crash_report()
        sys.exit(1)

    def _setup_logging(self):
        """Configura logging seguro para CI"""
        try:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler('pipeline.log'),
                    logging.StreamHandler()
                ]
            )
            self.logger = logging.getLogger('cocot-ci')
        except Exception as e:
            print(f"🆘 FALHA CRÍTICA NO LOGGING: {e}")
            sys.exit(1)

    def _verify_environment(self):
        """Verificações de segurança do ambiente"""
        if GitHubActionsShield.is_github():
            GitHubActionsShield.verify_environment()
            
            # Verifica permissões seguras
            if os.getuid() == 0:
                raise SecurityError("Execução como root detectada!")
                
            # Verifica variáveis sensíveis
            sensitive_vars = ['GITHUB_TOKEN', 'AWS_ACCESS_KEY']
            for var in sensitive_vars:
                if var in os.environ:
                    logging.warning(f"⚠️ Variável sensível detectada: {var}")

    def _load_config(self):
        """Carrega configuração com validação"""
        config_path = GitHubActionsShield.safe_path('config/config_execucao.json')
        self.config = {
            "timeout": 300,
            "max_retries": 3,
            "allowed_commands": ["python", "pytest"]
        }
        
        try:
            if config_path.exists():
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                    if not isinstance(user_config, dict):
                        raise ValueError("Configuração inválida")
                    self.config.update(user_config)
        except Exception as e:
            logging.error(f"Erro na configuração: {e}")
            GitHubActionsShield.annotate_error(f"Erro na configuração: {e}")

    def _setup_paths(self):
        """Configura paths com verificação de segurança"""
        self.workspace = GitHubActionsShield.safe_path('.')
        self.scripts_dir = GitHubActionsShield.safe_path('scripts')
        self.reports_dir = GitHubActionsShield.safe_path('relatorios')

    def _validate_command(self, command: List[str]):
        """Valida comandos para prevenir injection"""
        if not command:
            raise SecurityError("Comando vazio")
            
        if command[0] not in self.config['allowed_commands']:
            raise SecurityError(f"Comando não permitido: {command[0]}")
            
        for part in command:
            if ';' in part or '&&' in part or '||' in part:
                raise SecurityError(f"Possível command injection: {part}")

    def _run_safe_command(self, command: List[str], cwd: Path = None) -> bool:
        """Executa comando com todas as proteções"""
        self._validate_command(command)
        
        for attempt in range(1, self.max_retries + 1):
            try:
                result = subprocess.run(
                    command,
                    cwd=str(cwd) if cwd else None,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=self.timeout,
                    check=False,
                    shell=False  # Crucial para segurança
                )
                
                if result.stdout:
                    logging.info(f"Saída:\n{result.stdout[:1000]}")  # Limita tamanho
                if result.stderr:
                    logging.error(f"Erros:\n{result.stderr[:1000]}")
                    
                if result.returncode == 0:
                    return True
                    
                logging.warning(f"Tentativa {attempt}/{self.max_retries} falhou")
                
            except subprocess.TimeoutExpired:
                logging.error(f"Timeout após {self.timeout}s")
                GitHubActionsShield.annotate_error(f"Timeout no comando: {' '.join(command)}")
            except Exception as e:
                logging.error(f"Erro inesperado: {e}")
                GitHubActionsShield.annotate_error(f"Erro no comando: {type(e).__name__}")
                
            if attempt < self.max_retries:
                time.sleep(2 ** attempt)  # Backoff exponencial
                
        return False

    def _generate_crash_report(self):
        """Gera relatório de falha para diagnóstico"""
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "system": {
                "python": sys.version,
                "platform": sys.platform,
                "github_actions": GitHubActionsShield.is_github()
            },
            "environment": dict(os.environ)
        }
        
        try:
            crash_path = self.reports_dir / "crash_report.json"
            with open(crash_path, 'w') as f:
                json.dump(report, f, indent=2)
        except Exception as e:
            logging.error(f"Falha ao gerar crash report: {e}")

    def execute_pipeline(self):
        """Executa o pipeline com todas as proteções"""
        try:
            stages = [
                ("auditoria", [str(self.scripts_dir / "audit_runner.py")]),
                ("refatorador", [str(self.scripts_dir / "refatorador.py")]),
                ("testes", [str(self.scripts_dir / "test_runner.py")])
            ]
            
            for name, command in stages:
                logging.info(f"🚀 Iniciando estágio: {name.upper()}")
                if not self._run_safe_command(['python'] + command):
                    raise RuntimeError(f"Falha no estágio {name}")
                    
            logging.info("✅ Pipeline concluído com sucesso")
            return True
            
        except Exception as e:
            logging.critical(f"❌ Falha no pipeline: {e}", exc_info=True)
            GitHubActionsShield.annotate_error(f"Falha no pipeline: {str(e)}")
            return False

def main() -> int:
    """Entrypoint blindado"""
    try:
        executor = PipelineExecutor()
        success = executor.execute_pipeline()
        return 0 if success else 1
    except Exception as e:
        logging.critical(f"💥 Falha catastrófica: {e}", exc_info=True)
        GitHubActionsShield.annotate_error(f"Falha no executor: {str(e)}")
        return 1

if __name__ == "__main__":
    
# === Diagnóstico GPT-4o pós-pipeline (não interfere no CI) ===
if os.getenv("ENABLE_GPT4O_AUDIT", "false").lower() == "true":
    try:
        import openai
        prompt_path = Path("prompts/Super_Prompt_Auditor.txt")
        if prompt_path.exists():
            prompt_text = prompt_path.read_text(encoding="utf-8")
            openai.api_key = os.getenv("OPENAI_API_KEY")
            resultados = ["# Diagnóstico Final via GPT-4o"]
            for file in Path("src").rglob("*.py"):
                try:
                    codigo = file.read_text(encoding="utf-8")
                    resposta = openai.ChatCompletion.create(
                        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                        messages=[
                            {"role": "system", "content": "Você é um auditor técnico profissional."},
                            {"role": "user", "content": prompt_text + f"\n\nArquivo: {file}\nCódigo:\n{codigo}"}
                        ],
                        max_tokens=2048,
                        temperature=0.3
                    )
                    resultados.append(f"\n## {file}\n\n{resposta.choices[0].message.content.strip()}")
                except Exception as e:
                    resultados.append(f"\n## {file}\n\nErro: {e}")
            out_path = Path("relatorios/diagnostico_gpt4o.md")
            out_path.write_text("\n".join(resultados), encoding="utf-8")
            logging.info("✅ Diagnóstico GPT-4o salvo em relatorios/diagnostico_gpt4o.md")
        else:
            logging.warning("⚠️ Prompt GPT-4o não encontrado.")
    except Exception as err:
        logging.error(f"❌ GPT-4o falhou: {err}")


sys.exit(main())