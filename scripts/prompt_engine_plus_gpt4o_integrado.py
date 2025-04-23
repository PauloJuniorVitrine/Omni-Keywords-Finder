#!/usr/bin/env python3
# prompt_engine_plus.py - Motor de Execução de Prompts com Melhorias Avançadas

import json
import logging
import re
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import hashlib
import openai
from dataclasses import dataclass
from enum import Enum, auto
import redis
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class PromptEngineError(Exception):
    """Classe base para erros do PromptEngine"""
    pass

class SecurityError(PromptEngineError):
    """Erro de segurança no processamento de prompts"""
    pass

class CostLimitExceededError(PromptEngineError):
    """Erro ao exceder limites de custo"""
    pass

class PromptStrategy(Enum):
    SIMPLE = auto()
    STANDARD = auto()
    COMPLEX = auto()

@dataclass
class PromptMetrics:
    tokens_used: int
    estimated_cost: float
    response_time: float
    model_used: str

class LLMConnector:
    """Classe dedicada para gestão de conexões com LLMs"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._validate_config()
        self._init_llm()
    
    def _validate_config(self):
        required_keys = ['openai_api_key', 'primary_model']
        for key in required_keys:
            if key not in self.config:
                raise PromptEngineError(f"Configuração obrigatória faltando: {key}")
    
    def _init_llm(self):
        """Configuração segura da API"""
        openai.api_key = self.config['openai_api_key']
        openai.api_base = self.config.get('api_base', 'https://api.openai.com/v1')
        
        # Configuração de timeouts
        openai.request_timeout = self.config.get('timeout', 30)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((openai.error.APIConnectionError, openai.error.RateLimitError))
    )
    def execute(self, prompt: str, model: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Executa chamada ao LLM com retry automático"""
        model = model or self.config['primary_model']
        
        try:
            start_time = time.time()
            response = openai.ChatCompletion.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=kwargs.get('temperature', self.config.get('temperature', 0.7)),
                max_tokens=kwargs.get('max_tokens', self.config.get('max_tokens', 2000)),
            )
            response_time = time.time() - start_time
            
            return {
                'response': response.choices[0].message.content,
                'metadata': {
                    'model': model,
                    'tokens': response.usage.total_tokens,
                    'response_time': response_time
                }
            }
        except openai.error.InvalidRequestError as e:
            raise LLMExecutionError(f"Erro na requisição: {str(e)}")
        except Exception as e:
            raise LLMExecutionError(f"Falha na chamada ao LLM: {str(e)}")

class PromptValidator:
    """Classe dedicada para validação de prompts"""
    
    INJECTION_PATTERNS = [
        r"\{\{.*?\}\}", r"<\?.*?\?>", r"`.*?`",
        r"\$(?:\(.*?\)|\{.*?\})", r"eval\(.*?\)",
        r"import\s+(?:os|subprocess)", r"__.*?__"
    ]
    
    def __init__(self, security_level: str = 'high'):
        self.security_level = security_level
    
    def validate(self, prompt: str, context: Dict[str, Any]) -> bool:
        """Executa todas as validações necessárias"""
        self._check_injection(prompt)
        self._check_context(context)
        self._check_prompt_structure(prompt)
        return True
    
    def _check_injection(self, prompt: str):
        """Verifica padrões maliciosos"""
        for pattern in self.INJECTION_PATTERNS:
            if re.search(pattern, prompt, re.DOTALL):
                raise SecurityError(f"Padrão de injeção detectado: {pattern}")
    
    def _check_context(self, context: Dict[str, Any]):
        """Valida o contexto de injeção"""
        for key, value in context.items():
            if isinstance(value, str):
                for pattern in self.INJECTION_PATTERNS[:3]:
                    if re.search(pattern, value):
                        raise SecurityError(f"Injeção no contexto: {key}={value[:50]}...")
    
    def _check_prompt_structure(self, prompt: str):
        """Valida estrutura mínima do prompt"""
        if len(prompt.split()) < 20:
            raise PromptValidationError("Prompt muito curto (mínimo 20 palavras)")
        if not any(marker in prompt for marker in ['##', '"""', "'''"]):
            raise PromptValidationError("Prompt sem estrutura clara (use marcadores)")

class PromptAnalytics:
    """Monitoramento avançado de custos e performance"""
    
    def __init__(self):
        self.total_tokens = 0
        self.total_cost = 0.0
        self.history = []
    
    def track(self, response: Dict[str, Any]) -> PromptMetrics:
        """Calcula métricas da execução"""
        metadata = response['metadata']
        cost = self._calculate_cost(
            metadata['tokens'],
            metadata['model']
        )
        
        metrics = PromptMetrics(
            tokens_used=metadata['tokens'],
            estimated_cost=cost,
            response_time=metadata['response_time'],
            model_used=metadata['model']
        )
        
        self._update_global_metrics(metrics)
        return metrics
    
    def _calculate_cost(self, tokens: int, model: str) -> float:
        """Calcula custo baseado no modelo usado"""
        rates = {
            'gpt-4': 0.03/1000,
            'gpt-4-32k': 0.06/1000,
            'gpt-3.5-turbo': 0.002/1000
        }
        return tokens * rates.get(model, rates['gpt-4'])
    
    def _update_global_metrics(self, metrics: PromptMetrics):
        """Atualiza métricas globais"""
        self.total_tokens += metrics.tokens_used
        self.total_cost += metrics.estimated_cost
        self.history.append(metrics)
        
        if self.total_cost > 100:  # Limite de segurança
            raise CostLimitExceededError(f"Custo total excedeu $100: {self.total_cost:.2f}")

class RedisCache:
    """Cache distribuído usando Redis"""
    
    def __init__(self, host: str = 'localhost', port: int = 6379, ttl: int = 3600):
        self.client = redis.StrictRedis(
            host=host,
            port=port,
            decode_responses=True
        )
        self.ttl = ttl
    
    def get(self, key: str) -> Optional[str]:
        """Obtém valor do cache"""
        return self.client.get(key)
    
    def set(self, key: str, value: str) -> bool:
        """Define valor no cache com TTL"""
        return self.client.setex(key, self.ttl, value)
    
    def hash_get(self, key: str, field: str) -> Optional[str]:
        """Obtém valor de hash field"""
        return self.client.hget(key, field)
    
    def hash_set(self, key: str, field: str, value: str) -> int:
        """Define valor em hash field"""
        return self.client.hset(key, field, value)

class PromptEngine:
    """Versão turbinada do PromptEngine com todas as melhorias"""
    
    def __init__(self, prompts_dir: Path, config: Dict[str, Any]):
        self._validate_init_params(prompts_dir, config)
        
        self.prompts_dir = prompts_dir
        self.config = config
        self.logger = self._setup_logging()
        self.llm = LLMConnector(config['llm'])
        self.validator = PromptValidator(config.get('security_level', 'high'))
        self.analytics = PromptAnalytics()
        self.cache = RedisCache(**config.get('redis', {})) if config.get('use_redis') else None
        self.prompt_templates = self._load_all_templates()
    
    def _validate_init_params(self, prompts_dir: Path, config: dict):
        """Validação rigorosa dos parâmetros iniciais"""
        if not isinstance(prompts_dir, Path):
            raise PromptValidationError("prompts_dir deve ser um objeto Path")
            
        if not prompts_dir.exists():
            raise PromptValidationError(f"Diretório não existe: {prompts_dir}")
    
    def _setup_logging(self):
        """Configura logging estruturado"""
        logger = logging.getLogger('prompt-engine-plus')
        logger.setLevel(logging.DEBUG if self.config.get('debug') else logging.INFO)
        
        handler = logging.FileHandler('prompt_engine_plus.log')
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
        ))
        logger.addHandler(handler)
        
        return logger
    
    def _load_all_templates(self) -> Dict[str, str]:
        """Carrega todos os templates na inicialização"""
        templates = {}
        for template_file in self.prompts_dir.glob('*.txt'):
            try:
                content = template_file.read_text(encoding='utf-8')
                self.validator.validate(content, {})
                templates[template_file.stem] = content
            except Exception as e:
                self.logger.error(f"Falha ao carregar template {template_file.name}: {str(e)}")
        return templates
    
    def _determine_strategy(self, context: Dict[str, Any]) -> PromptStrategy:
        """Determina a estratégia de prompt baseada no contexto"""
        complexity = context.get('complexity', 'medium')
        return {
            'low': PromptStrategy.SIMPLE,
            'medium': PromptStrategy.STANDARD,
            'high': PromptStrategy.COMPLEX
        }.get(complexity, PromptStrategy.STANDARD)
    
    def _build_hierarchical_prompt(self, base_prompt: str, context: Dict[str, Any]) -> str:
        """Constroi prompt hierárquico"""
        components = [
            self.prompt_templates.get('header', ''),
            base_prompt,
            self.prompt_templates.get(f"footer_{context.get('domain', 'default')}", '')
        ]
        return "\n\n".join(filter(None, components))
    
    def _get_cached_response(self, prompt_hash: str) -> Optional[str]:
        """Obtém resposta do cache se disponível"""
        if not self.cache:
            return None
        return self.cache.get(f"prompt:{prompt_hash}")
    
    def _cache_response(self, prompt_hash: str, response: str):
        """Armazena resposta no cache"""
        if self.cache:
            self.cache.set(f"prompt:{prompt_hash}", response)
    
    def execute_prompt(self, prompt_type: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execução turbinada do prompt com todas as melhorias"""
        execution_id = f"exec_{hashlib.sha1(str(time.time()).encode()).hexdigest()[:8]}"
        context = context or {}
        
        try:
            # 1. Determinar estratégia
            strategy = self._determine_strategy(context)
            prompt_key = f"{prompt_type}_{strategy.name.lower()}"
            
            # 2. Obter template base
            base_prompt = self.prompt_templates.get(prompt_key)
            if not base_prompt:
                raise PromptValidationError(f"Template não encontrado: {prompt_key}")
            
            # 3. Construir prompt hierárquico
            full_prompt = self._build_hierarchical_prompt(base_prompt, context)
            
            # 4. Validar segurança
            self.validator.validate(full_prompt, context)
            
            # 5. Verificar cache
            prompt_hash = hashlib.sha256(full_prompt.encode()).hexdigest()
            if cached := self._get_cached_response(prompt_hash):
                return {'status': 'success', 'data': cached, 'cached': True}
            
            # 6. Executar no LLM
            response = self.llm.execute(full_prompt)
            
            # 7. Processar resposta
            processed = self._process_response(response['response'])
            
            # 8. Armazenar em cache
            self._cache_response(prompt_hash, processed)
            
            # 9. Coletar métricas
            metrics = self.analytics.track(response)
            
            return {
                'status': 'success',
                'data': processed,
                'metrics': metrics.__dict__,
                'execution_id': execution_id
            }
            
        except Exception as e:
            self.logger.error(f"Falha na execução {execution_id}: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e),
                'execution_id': execution_id
            }
    
    def _process_response(self, raw_response: str) -> Union[Dict, str]:
        """Processamento avançado de respostas"""
        try:
            # Tentativa 1: Extração de JSON
            json_match = re.search(r'```json\n(.+?)\n```', raw_response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            
            # Tentativa 2: JSON direto
            if raw_response.strip().startswith('{'):
                return json.loads(raw_response)
            
            # Tentativa 3: YAML (simplificado)
            if re.match(r'^\s*[\w-]+:', raw_response):
                import yaml
                return yaml.safe_load(raw_response)
            
            # Fallback: Estruturação automática
            return self._structure_arbitrary_response(raw_response)
        except Exception:
            return {'raw_response': raw_response}
    
    def _structure_arbitrary_response(self, text: str) -> Dict[str, Any]:
        """Tenta estruturar automaticamente respostas não padronizadas"""
        sections = re.split(r'\n##\s+', text)
        if len(sections) > 1:
            return {
                section.split('\n')[0].lower(): '\n'.join(section.split('\n')[1:])
                for section in sections if section.strip()
            }
        return {'content': text}

# Exemplo de uso avançado
if __name__ == "__main__":
    config = {
        'llm': {
            'openai_api_key': 'sua-chave-aqui',
            'primary_model': 'gpt-4',
            'temperature': 0.7,
            'max_tokens': 2000,
            'timeout': 30
        },
        'redis': {
            'host': 'localhost',
            'port': 6379,
            'ttl': 86400
        },
        'use_redis': True,
        'security_level': 'paranoid',
        'debug': True
    }
    
    engine = PromptEngine(
        prompts_dir=Path(__file__).parent / "prompts",
        config=config
    )
    
    resultado = engine.execute_prompt(
        prompt_type='e2e',
        context={
            'modulo': 'sistema_de_pagamentos',
            'linguagem': 'Python',
            'framework': 'Playwright',
            'complexity': 'high',
            'domain': 'financial'
        }
    )
    
    print(json.dumps(resultado, indent=2))

# === Análise complementar com GPT-4o (não destrutiva) ===
if os.getenv("ENABLE_GPT4O_AUDIT", "false").lower() == "true":
    try:
        prompt_path = Path("prompts/Super_Prompt_Auditor.txt")
        if prompt_path.exists():
            prompt_text = prompt_path.read_text(encoding="utf-8")
            for file in Path("src").rglob("*.py"):
                content = file.read_text(encoding="utf-8")
                print(f"\n### Análise GPT-4o: {file}")
                gpt_result = openai.ChatCompletion.create(
                    model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                    messages=[
                        {"role": "system", "content": "Você é um auditor técnico profissional."},
                        {"role": "user", "content": prompt_text + f"\n\nArquivo: {file}\nCódigo:\n{content}"}
                    ],
                    temperature=0.2,
                    max_tokens=2048
                )
                print(gpt_result.choices[0].message.content.strip())
        else:
            print("[GPT-4o] Prompt auditor não encontrado.")
    except Exception as err:
        print(f"[GPT-4o] Erro durante execução: {err}")