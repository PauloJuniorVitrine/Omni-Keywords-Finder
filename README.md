# Omni Keywords Finder - Auditoria Automática com CoCoT Precision

Sistema completo para auditoria, refatoração e testes de código-fonte com base na metodologia **CoCoT Modular 2025**, integrado com **GitHub Actions** e suporte total ao **GPT-4** ou **DeepSeek Coder** via API.

---

## 📁 Estrutura do Projeto

```
Nova pasta/
├── .github/workflows/python-ci.yml       # Pipeline CI/CD
├── config/                               # Configurações da execução
│   ├── audit_config.json
│   ├── config.json
│   ├── config_execucao.json
│   ├── prompt_engine_config.json
│   ├── refatorador_config.json
│   └── test_config.json
├── prompts/                              # Prompts de testes e auditoria
│   ├── Super_Prompt_Auditor.txt
│   ├── prompt_base_unitario.txt
│   ├── prompt_base_integracao.txt
│   ├── prompt_base_carga.txt
│   └── prompt_base_e2e.txt
├── scripts/                              # Scripts principais
│   ├── audit_runner.py
│   ├── executor.py
│   ├── prompt_engine_plus.py
│   ├── refatorador.py
│   └── test_runner.py
├── requirements.txt                      # Dependências Python
└── README.md                             # Este documento
```

---

## ⚙️ Pré-Requisitos

- Python 3.10+
- GitHub com Actions habilitadas
- Chave de API GPT-4 / DeepSeek configurada como secret (`OPENAI_API_KEY`)
- Redis opcional para cache

---

## 🚀 Como Usar

### Execução Manual Local
```bash
pip install -r requirements.txt
python scripts/executor.py --config config/config_execucao.json
```

### Execução via GitHub Actions
1. Suba o repositório para o GitHub
2. Configure as variáveis no repositório:
   - `OPENAI_API_KEY`
   - `REDIS_PASSWORD` (opcional)
3. O fluxo será executado automaticamente em:
   - `push` para `main` ou `develop`
   - `pull_request` para `main`
   - ou manualmente via `workflow_dispatch`

---

## 🧪 Ciclo Automatizado

1. **Audit Runner**: verifica estrutura e qualidade
2. **Prompt Engine**: gera melhorias e validações
3. **Refatorador**: aplica recomendações
4. **Test Runner**: executa testes unitários, integração, carga e E2E
5. **Executor**: orquestra o ciclo até a aprovação total

---

## ✅ Metodologia Aplicada

- **CoCoT Modular 2025**
- Auditoria técnica com 24 blocos
- Refatoração não destrutiva
- Testes determinísticos, defensivos e de performance
- Templates de prompts prontos para cluster de testes

---

## 📊 Relatórios e Logs

- Logs salvos em `logs/`
- Resultados de auditoria podem ser expandidos com exports `.md`, `.json` ou Prometheus

---

## 📌 Dicas Finais

- Personalize os prompts em `/prompts`
- Use `modo_dry_run` para validar refatorações antes de aplicar
- Acompanhe consumo com `analytics.cost_limits`

---

**Pronto para produção. Automatize, audite, valide.**
