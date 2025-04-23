# 🧪 Guia de Testes

O Omni Keywords Finder utiliza `pytest` como framework principal de testes automatizados.

---

## 📁 Estrutura dos Testes

```
src/
├── 1-loggin/tests/
├── 2-Theme Manager/tests/
├── 3-data base/tests db/
├── 4-colector/tests colector/
├── 5-keyword validation/tests keywords validation/
├── 6-api/tests api/
```

---

## ▶️ Executar todos os testes

```bash
pytest
```

## ▶️ Executar testes de um módulo específico

```bash
pytest src/4-colector/tests\ colector/test_google_trends.py
```

## 🧪 Escrevendo um novo teste

- Testes devem começar com `test_`
- Usar `assert` para validação
- Testes unitários devem ser isolados e reprodutíveis

```python
def test_soma_simples():
    assert 1 + 1 == 2
```

---

## 💡 Dicas

- Use `pytest --maxfail=1 --disable-warnings` para depuração rápida
- Combine com `coverage.py` para análise de cobertura

---

