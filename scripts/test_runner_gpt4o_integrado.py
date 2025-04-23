#!/usr/bin/env python3
# test_runner.py - Versão Integrada com PromptEngine

import argparse
import json
import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, NoReturn
from dataclasses import dataclass
from enum import Enum, auto
import resource
from prompt_engine import PromptEngine  # Importando nosso PromptEngine turbinado

# Configurações padrão
MAX_RETRIES = 3
TIMEOUT_SECONDS = 60
MEMORY_LIMIT_MB = 1024

class TestType(Enum):
    UNIT = "unitario"
    INTEGRATION = "integracao"
    E2E = "e2e"
    LOAD = "carga"

@dataclass
class TestResult:
    status: str
    duration: float
    output: str = ""
    error: str = ""
    generated_code: str = ""

class TestGenerator:
    """Gerencia a geração de testes usando PromptEngine"""
    
    def __init__(self, config: Dict[str, Any]):
        self.engine = PromptEngine(
            prompts_dir=Path(__file__).parent / "prompts",
            config=config
        )
        self.logger = logging.getLogger('test-generator')
    
    def generate_test(self, test_type: TestType, context: Dict[str, Any]) -> TestResult:
        """Gera código de teste usando o PromptEngine"""
        result = TestResult(status="pending", duration=0)
        start_time = time.time()
        
        try:
            response = self.engine.execute_prompt(
                prompt_type=test_type.value,
                context=context
            )
            
            if response['status'] != 'success':
                result.status = "generation_failed"
                result.error = response.get('message', 'Unknown error')
                return result
            
            generated_code = response['data'].get('raw_response', '')
            if not generated_code:
                result.status = "empty_response"
                result.error = "O LLM retornou uma resposta vazia"
                return result
            
            result.status = "generated"
            result.generated_code = generated_code
            result.duration = time.time() - start_time
            
            # Salva o teste gerado em arquivo
            test_file = self._save_test_file(test_type, generated_code)
            result.output = f"Teste salvo em {test_file}"
            
        except Exception as e:
            result.status = "error"
            result.error = str(e)
            self.logger.error(f"Falha na geração de teste: {e}", exc_info=True)
        
        return result
    
    def _save_test_file(self, test_type: TestType, code: str) -> Path:
        """Salva o código gerado em um arquivo temporário"""
        tests_dir = Path(__file__).parent / "generated_tests"
        tests_dir.mkdir(exist_ok=True)
        
        timestamp = int(time.time())
        test_file = tests_dir / f"test_{test_type.value}_{timestamp}.py"
        
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(code)
        
        return test_file

class FortifiedTestRunner:
    """Executor de testes com integração completa ao PromptEngine"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.test_generator = TestGenerator(config)
        self._setup_logging()
        self._setup_emergency_shutdown()
        self._configure_system_limits()
    
    def _setup_logging(self):
        """Configura logging detalhado"""
        logging.basicConfig(
            level=logging.DEBUG if self.config.get('debug') else logging.INFO,
            format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
            handlers=[
                logging.FileHandler('test_runner.log'),
                logging.StreamHandler()
            ]
        )
    
    def _setup_emergency_shutdown(self):
        """Configura handlers para sinais críticos"""
        signal.signal(signal.SIGTERM, self._emergency_shutdown)
        signal.signal(signal.SIGINT, self._emergency_shutdown)
    
    def _emergency_shutdown(self, signum, frame) -> NoReturn:
        """Limpeza segura em caso de falha catastrófica"""
        logging.critical(f"Emergency shutdown (signal {signum})")
        sys.exit(1)
    
    def _configure_system_limits(self):
        """Aplica limites de recursos do sistema"""
        try:
            resource.setrlimit(resource.RLIMIT_CPU, (TIMEOUT_SECONDS, TIMEOUT_SECONDS))
            resource.setrlimit(
                resource.RLIMIT_AS,
                (MEMORY_LIMIT_MB * 1024 * 1024, MEMORY_LIMIT_MB * 1024 * 1024)
            )
        except Exception as e:
            logging.error(f"Failed to set system limits: {e}")

    def run_test(self, test_type: TestType, context: Dict[str, Any]) -> TestResult:
        """Executa o fluxo completo: geração + execução do teste"""
        # 1. Geração do teste
        gen_result = self.test_generator.generate_test(test_type, context)
        if gen_result.status != "generated":
            return gen_result
        
        # 2. Execução do teste gerado
        test_file = Path(gen_result.output.split()[-1])
        exec_result = self._execute_test(test_file)
        
        # Combina resultados
        final_result = TestResult(
            status=exec_result.status,
            duration=gen_result.duration + exec_result.duration,
            generated_code=gen_result.generated_code,
            output=exec_result.output,
            error=exec_result.error
        )
        
        return final_result
    
    def _execute_test(self, test_file: Path) -> TestResult:
        """Executa um teste gerado em ambiente controlado"""
        result = TestResult(status="pending", duration=0)
        start_time = time.time()
        
        try:
            process = subprocess.Popen(
                [sys.executable, str(test_file)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=self._get_safe_env()
            )
            
            try:
                stdout, stderr = process.communicate(timeout=TIMEOUT_SECONDS)
                result.duration = time.time() - start_time
                
                if process.returncode == 0:
                    result.status = "success"
                    result.output = stdout
                else:
                    result.status = "failed"
                    result.error = stderr
                
            except subprocess.TimeoutExpired:
                process.kill()
                result.status = "timeout"
                result.error = f"Teste excedeu o tempo limite de {TIMEOUT_SECONDS}s"
                
        except Exception as e:
            result.status = "error"
            result.error = str(e)
            logging.error(f"Erro na execução do teste: {e}", exc_info=True)
        
        return result
    
    def _get_safe_env(self) -> Dict[str, str]:
        """Retorna ambiente seguro para execução de testes"""
        env = os.environ.copy()
        # Remove variáveis sensíveis
        for var in ["API_KEY", "SECRET"]:
            env.pop(var, None)
        return env

def main():
    parser = argparse.ArgumentParser(description="Executador de testes integrado com PromptEngine")
    parser.add_argument("test_type", choices=[t.value for t in TestType], help="Tipo de teste a ser gerado e executado")
    parser.add_argument("--module", required=True, help="Módulo/alvo a ser testado")
    parser.add_argument("--language", default="Python", help="Linguagem de programação para os testes")
    parser.add_argument("--framework", help="Framework de teste a ser utilizado")
    parser.add_argument("--config", default="config.json", help="Arquivo de configuração do PromptEngine")
    
    args = parser.parse_args()
    
    # Carrega configuração
    with open(args.config) as f:
        config = json.load(f)
    
    # Prepara contexto
    context = {
        "modulo": args.module,
        "linguagem": args.language,
        "framework": args.framework or "",
        "complexity": "high"  # Pode ser parametrizado
    }
    
    runner = FortifiedTestRunner(config)
    test_type = TestType(args.test_type)
    result = runner.run_test(test_type, context)
    
    # Saída formatada
    print("\n=== Resultado do Teste ===")
    print(f"Status: {result.status}")
    if result.error:
        print(f"Erro: {result.error}")
    print(f"Duração: {result.duration:.2f}s")
    print(f"Arquivo: {result.output if 'Arquivo' in result.output else 'N/A'}")
    
    if result.status == "success":
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()

# === Diagnóstico complementar com GPT-4o ===
if os.getenv("ENABLE_GPT4O_AUDIT", "false").lower() == "true":
    try:
        import openai
        from pathlib import Path
        prompt_path = Path("prompts/Super_Prompt_Auditor.txt")
        if prompt_path.exists():
            prompt = prompt_path.read_text(encoding="utf-8")
            file_path = Path("src") / args.module
            if file_path.exists():
                code = file_path.read_text(encoding="utf-8")
                openai.api_key = os.getenv("OPENAI_API_KEY")
                result = openai.ChatCompletion.create(
                    model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                    messages=[
                        {"role": "system", "content": "Você é um auditor técnico profissional."},
                        {"role": "user", "content": prompt + f"\n\nArquivo: {file_path}\nCódigo:\n{code}"}
                    ],
                    temperature=0.2,
                    max_tokens=2048
                )
                print("\n=== Diagnóstico GPT-4o ===")
                print(result.choices[0].message.content.strip())
            else:
                print(f"[GPT-4o] Arquivo não encontrado: {file_path}")
        else:
            print("[GPT-4o] Prompt não encontrado.")
    except Exception as e:
        print(f"[GPT-4o] Erro: {e}")