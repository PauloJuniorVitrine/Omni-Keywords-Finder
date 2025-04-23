#!/usr/bin/env python3
# audit_runner.py - Versão Blindada para GitHub Actions

import json
import logging
import os
import subprocess
import sys
import traceback
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Dict, List, Optional, NoReturn
import signal

class GitHubActionsIntegration:
    """Helper para integração com GitHub Actions"""
    @staticmethod
    def is_github_actions() -> bool:
        return os.getenv("GITHUB_ACTIONS") == "true"
    
    @staticmethod
    def annotate_error(message: str, file: str = None, line: str = None, col: str = None) -> None:
        if GitHubActionsIntegration.is_github_actions():
            parts = [f"file={file}"] if file else []
            parts += [f"line={line}"] if line else []
            parts += [f"col={col}"] if col else []
            loc = ",".join(parts)
            loc_prefix = f" {loc}" if loc else ""
            print(f"::error{loc_prefix}::{message.replace('\n', '%0A')}")

    @staticmethod
    def set_output(name: str, value: str) -> None:
        if GitHubActionsIntegration.is_github_actions():
            with open(os.getenv("GITHUB_OUTPUT"), "a") as f:
                print(f"{name}={value}", file=f)

class RetryOperation:
    """Decorator para operações com retentativa"""
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
            raise last_error
        return wrapper

class SafeAuditor:
    def __init__(self) -> None:
        """Inicialização robusta com tratamento de falhas"""
        self._setup_signal_handlers()
        self._setup_logging()
        self._validate_environment()
        self.base_dir = self._resolve_base_dir()
        self.relatorios_dir = self._ensure_dir(self.base_dir / "relatorios")
        self.config = self._load_config_safely()
        self._init_metrics()
        self.file_hashes = {}
        logging.info("Auditor inicializado com sucesso")

    def _setup_signal_handlers(self) -> None:
        """Configura handlers para sinais de interrupção"""
        signal.signal(signal.SIGINT, self._handle_interrupt)
        signal.signal(signal.SIGTERM, self._handle_interrupt)

    def _handle_interrupt(self, signum, frame) -> NoReturn:
        """Handler para sinais de interrupção"""
        logging.critical(f"Recebido sinal {signum}, encerrando...")
        sys.exit(1)

    def _setup_logging(self) -> None:
        """Configura logging com fallback para GitHub Actions"""
        try:
            log_level = logging.DEBUG if os.getenv("DEBUG") else logging.INFO
            
            if GitHubActionsIntegration.is_github_actions():
                fmt = '%(levelname)s::%(message)s'
            else:
                fmt = '%(asctime)s - %(levelname)s - %(message)s'
            
            logging.basicConfig(
                level=log_level,
                format=fmt,
                handlers=[
                    logging.FileHandler('audit_secure.log'),
                    logging.StreamHandler()
                ]
            )
        except Exception:
            logging.basicConfig(level=logging.INFO)

    def _validate_environment(self) -> None:
        """Valida variáveis de ambiente necessárias"""
        if GitHubActionsIntegration.is_github_actions():
            required_vars = ["GITHUB_WORKSPACE", "GITHUB_REPOSITORY"]
            missing = [var for var in required_vars if not os.getenv(var)]
            if missing:
                raise RuntimeError(f"Variáveis de ambiente faltando: {', '.join(missing)}")

    def _resolve_base_dir(self) -> Path:
        """Resolve o diretório base com verificações de segurança"""
        try:
            base = Path(os.getenv("GITHUB_WORKSPACE", Path(__file__).resolve().parent.parent))
            
            # Verificação de estrutura mínima
            required = ["scripts", "config"]
            missing = [d for d in required if not (base / d).exists()]
            if missing:
                raise RuntimeError(f"Diretórios obrigatórios faltando: {', '.join(missing)}")
                
            return base
        except Exception as e:
            GitHubActionsIntegration.annotate_error(f"Erro ao resolver diretório base: {e}")
            raise

    def _ensure_dir(self, path: Path) -> Path:
        """Cria diretório com verificações de permissão"""
        try:
            path.mkdir(parents=True, exist_ok=True)
            if not os.access(path, os.W_OK):
                raise RuntimeError(f"Sem permissão de escrita em {path}")
            return path
        except Exception as e:
            GitHubActionsIntegration.annotate_error(f"Falha ao criar diretório {path}: {e}")
            raise

    def _load_config_safely(self) -> Dict:
        """Carrega configuração com múltiplos fallbacks"""
        config_path = self.base_dir / "config" / "audit_config.json"
        default_config = {
            "required_folders": ["scripts", "config", "src"],
            "strict_mode": False,
            "fail_threshold": 85.0,
            "max_workers": 4,
            "timeout": 30
        }

        try:
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    if not isinstance(config, dict):
                        raise ValueError("Configuração deve ser um dicionário")
                    return {**default_config, **config}
        except Exception as e:
            logging.warning(f"Usando configuração padrão - Erro: {e}")

        return default_config

    def _init_metrics(self) -> None:
        """Inicializa métricas opcionais"""
        try:
            from prometheus_client import Counter, Gauge
            self.metrics = {
                'files': Counter('audit_files', 'Arquivos auditados'),
                'errors': Counter('audit_errors', 'Erros encontrados'),
                'duration': Gauge('audit_duration', 'Duração da auditoria')
            }
        except ImportError:
            self.metrics = None
            logging.warning("Métricas desativadas - Prometheus não disponível")

    @RetryOperation(max_attempts=3, delay=2)
    def _safe_subprocess(self, cmd: List[str]) -> Dict:
        """Executa subprocesso com timeout e retentativa"""
        try:
            result = subprocess.run(
                cmd,
                timeout=self.config.get("timeout", 30),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            return {
                "status": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr
            }
        except subprocess.TimeoutExpired:
            logging.error(f"Timeout no comando: {' '.join(cmd)}")
            return {"status": False, "error": "Timeout"}
        except Exception as e:
            logging.error(f"Erro no subprocesso: {e}")
            return {"status": False, "error": str(e)}

    def _atomic_write(self, path: Path, content: str) -> bool:
        """Escrita atômica com arquivo temporário"""
        temp_path = path.with_suffix('.tmp')
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(content)
            os.replace(temp_path, path)
            return True
        except Exception as e:
            logging.error(f"Falha na escrita atômica: {e}")
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass
            return False

    def run_audit(self) -> Optional[Dict]:
        """Execução principal da auditoria"""
        start_time = time.time()
        report = {
            "metadata": {
                "start_time": datetime.utcnow().isoformat(),
                "config": self.config,
                "environment": {
                    "github_actions": GitHubActionsIntegration.is_github_actions(),
                    "python_version": sys.version
                }
            },
            "results": {}
        }

        try:
            # Verificação de pastas obrigatórias
            for folder in self.config["required_folders"]:
                folder_path = self.base_dir / folder
                report["results"][folder] = self._check_folder(folder_path)

            # Verificação de segurança adicional
            report["security_checks"] = self._run_security_checks()

            # Análise estática condicional
            if self.config.get("enable_static_analysis", False):
                report["static_analysis"] = self._run_static_analysis()

            report["metadata"]["end_time"] = datetime.utcnow().isoformat()
            report["metadata"]["duration_seconds"] = round(time.time() - start_time, 2)
            
            if self.metrics:
                self.metrics["duration"].set(report["metadata"]["duration_seconds"])
            
            return report

        except Exception as e:
            logging.error(f"Erro durante auditoria: {e}", exc_info=True)
            GitHubActionsIntegration.annotate_error(f"Falha na auditoria: {e}")
            return None

    def _check_folder(self, path: Path) -> Dict:
        """Verificação resiliente de pasta"""
        result = {
            "exists": path.exists(),
            "valid": False,
            "files": [],
            "error": None
        }

        if not result["exists"]:
            result["error"] = "Diretório não encontrado"
            return result

        try:
            if not path.is_dir():
                result["error"] = "Não é um diretório"
                return result

            result["valid"] = True
            max_workers = min(self.config["max_workers"], 10)  # Limita para evitar sobrecarga
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(self._audit_file, f): f
                    for f in path.glob('*')
                    if f.is_file()
                }

                for future in as_completed(futures, timeout=self.config.get("timeout", 30)*2):
                    try:
                        result["files"].append(future.result())
                    except TimeoutError:
                        filepath = futures[future]
                        logging.warning(f"Timeout ao processar {filepath}")
                        result["files"].append({"path": str(filepath), "error": "timeout"})
                    except Exception as e:
                        filepath = futures[future]
                        logging.warning(f"Erro ao processar {filepath}: {e}")
                        result["files"].append({"path": str(filepath), "error": str(e)})

        except Exception as e:
            logging.error(f"Erro ao verificar {path}: {e}")
            result["valid"] = False
            result["error"] = str(e)

        return result

    def _audit_file(self, filepath: Path) -> Dict:
        """Análise individual de arquivo com tratamento completo"""
        file_report = {
            "path": str(filepath.relative_to(self.base_dir)),
            "valid": False,
            "size": None,
            "hash": None,
            "error": None
        }

        try:
            # Verificação básica
            file_report["size"] = filepath.stat().st_size
            if file_report["size"] == 0:
                raise RuntimeError("Arquivo vazio")

            # Cálculo de hash
            file_report["hash"] = self._calculate_hash(filepath)
            
            # Verificação de conteúdo
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                if not content.strip():
                    raise RuntimeError("Arquivo sem conteúdo válido")

            file_report["valid"] = True

        except UnicodeDecodeError:
            file_report["error"] = "Encoding inválido (não UTF-8)"
        except Exception as e:
            file_report["error"] = str(e)
            if self.metrics:
                self.metrics["errors"].inc()

        if self.metrics:
            self.metrics["files"].inc()

        return file_report

    def _calculate_hash(self, path: Path) -> str:
        """Geração de hash segura"""
        try:
            with open(path, 'rb') as f:
                return sha256(f.read()).hexdigest()
        except Exception as e:
            logging.warning(f"Falha ao gerar hash para {path}: {e}")
            return ""

    def _run_security_checks(self) -> Dict:
        """Executa verificações de segurança adicionais"""
        checks = {
            "file_permissions": self._check_file_permissions(),
            "sensitive_data": self._check_sensitive_data()
        }
        return checks

    def _check_file_permissions(self) -> Dict:
        """Verifica permissões de arquivos sensíveis"""
        sensitive_files = [
            self.base_dir / "config" / "secrets.json",
            self.base_dir / ".env"
        ]
        
        results = {}
        for filepath in sensitive_files:
            try:
                if filepath.exists():
                    mode = oct(filepath.stat().st_mode)[-3:]
                    results[str(filepath)] = {
                        "permissions": mode,
                        "secure": mode in ("600", "400")
                    }
            except Exception as e:
                results[str(filepath)] = {"error": str(e)}
        
        return results

    def _check_sensitive_data(self) -> Dict:
        """Verifica padrões de dados sensíveis"""
        patterns = {
            "api_key": r"(?i)api[_-]?key",
            "password": r"(?i)passw(or)?d",
            "secret": r"(?i)secret"
        }
        
        try:
            cmd = ["grep", "-rE", "|".join(patterns.values()), str(self.base_dir)]
            result = self._safe_subprocess(cmd)
            return {
                "found": result["status"],
                "output": result["output"] if result["status"] else None
            }
        except Exception as e:
            return {"error": str(e)}

    def _run_static_analysis(self) -> Dict:
        """Executa análise estática condicional"""
        tools = ["bandit", "pylint", "mypy"]
        results = {}
        
        for tool in tools:
            try:
                cmd = [tool, str(self.base_dir / "src")]
                result = self._safe_subprocess(cmd)
                results[tool] = {
                    "success": result["status"],
                    "output": result["output"],
                    "error": result["error"]
                }
            except Exception as e:
                results[tool] = {"error": str(e)}
        
        return results

    def generate_reports(self, data: Dict) -> bool:
        """Geração de relatórios com rollback automático"""
        if not data:
            logging.error("Dados inválidos para relatório")
            return False

        try:
            # JSON Report
            json_report = json.dumps(data, indent=2)
            json_success = self._atomic_write(
                self.relatorios_dir / "audit_report.json",
                json_report
            )

            # Markdown Summary
            md_success = self._atomic_write(
                self.relatorios_dir / "audit_summary.md",
                self._generate_markdown(data)
            )

            # GitHub Actions Output
            if GitHubActionsIntegration.is_github_actions():
                GitHubActionsIntegration.set_output("audit_status", "success" if json_success and md_success else "failed")
                GitHubActionsIntegration.set_output("audit_duration", str(data["metadata"].get("duration_seconds", 0)))

            return json_success and md_success

        except Exception as e:
            logging.error(f"Falha ao gerar relatórios: {e}")
            GitHubActionsIntegration.annotate_error(f"Falha ao gerar relatórios: {e}")
            return False

    def _generate_markdown(self, data: Dict) -> str:
        """Geração segura de relatório Markdown"""
        try:
            lines = [
                "# Relatório de Auditoria",
                f"**Data**: {datetime.utcnow().isoformat()}",
                f"**Duração**: {data['metadata'].get('duration_seconds', 0)} segundos",
                "## Sumário"
            ]

            # Resumo por pasta
            for folder, result in data["results"].items():
                status = "✅" if result.get("valid") else "❌"
                lines.append(f"- {folder}: {status} ({len(result.get('files', []))} arquivos)")

            # Verificações de segurança
            if "security_checks" in data:
                lines.append("\n## Verificações de Segurança")
                for check, result in data["security_checks"].items():
                    lines.append(f"- {check}: {'✅' if result.get('secure') else '❌'}")

            return "\n".join(lines)
        except Exception as e:
            logging.error(f"Falha ao gerar Markdown: {e}")
            return "# Relatório de Auditoria\nErro na geração do relatório"

def main() -> int:
    """Entrypoint blindado para execução no GitHub Actions"""
    try:
        # Configura tratamento de exceções não capturadas
        sys.excepthook = lambda exc_type, exc_value, exc_traceback: (
            logging.critical("Exceção não capturada:", exc_info=(exc_type, exc_value, exc_traceback)),
            GitHubActionsIntegration.annotate_error(f"Exceção não capturada: {exc_value}"),
            sys.exit(1)
        )

        auditor = SafeAuditor()
        report = auditor.run_audit()
        
        if not report:
            logging.error("Auditoria falhou sem gerar relatório")
            return 1

        success = auditor.generate_reports(report)
        return 0 if success else 1

    except Exception as e:
        logging.critical(f"Falha catastrófica: {e}", exc_info=True)
        GitHubActionsIntegration.annotate_error(f"Falha catastrófica: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())

# === GPT-4o Análise Complementar ===
import openai

def gpt4o_analisar_codigo(file_path, codigo, prompt_base):
    try:
        openai.api_key = os.getenv("OPENAI_API_KEY")
        resposta = openai.ChatCompletion.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            messages=[
                {"role": "system", "content": "Você é um auditor técnico profissional."},
                {"role": "user", "content": prompt_base + f"\n\nArquivo: {file_path}\nCódigo:\n{codigo}"}
            ],
            max_tokens=2048,
            temperature=0.2
        )
        return resposta.choices[0].message.content.strip()
    except Exception as e:
        return f"[GPT-4o ERRO em {file_path}]: {e}"

# Apenas executar se tiver prompt e chave
gpt4o_prompt_path = os.getenv("GPT4O_PROMPT_FILE", "prompts/Super_Prompt_Auditor.txt")
if Path(gpt4o_prompt_path).exists():
    prompt_conteudo = Path(gpt4o_prompt_path).read_text(encoding="utf-8")
    resultados_md = ["\n\n# Diagnóstico Técnico via GPT-4o"]
    for file in Path("src").rglob("*.py"):
        try:
            codigo = file.read_text(encoding="utf-8")
            resultado = gpt4o_analisar_codigo(str(file), codigo, prompt_conteudo)
            resultados_md.append(f"\n\n## {file}\n\n{resultado}")
        except Exception as e:
            resultados_md.append(f"\n\n## {file}\n\nErro ao ler/analisar: {e}")
    Path("relatorios/audit_summary.md").write_text(
        Path("relatorios/audit_summary.md").read_text(encoding="utf-8") + "\n\n" + "\n".join(resultados_md),
        encoding="utf-8"
    )