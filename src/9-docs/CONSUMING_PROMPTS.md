# 🧷 Guia para Sistemas que Consomem os ZIPs de Prompts

Este documento explica como **outros sistemas** podem utilizar os `.zip` exportados pelo Omni Keywords Finder para publicar ou transformar os conteúdos gerados.

## 📦 Estrutura dos ZIPs

```
/exportado.zip
├── nicho_tecnologia/
│   ├── prompts_blog.txt
│   ├── prompts_instagram.txt
│   └── prompts_youtube.txt
```

## 🔁 Integração Recomendada

1. Agende verificação diária
2. Baixe `.zip` da API
3. Extraia os arquivos
4. Publique ou armazene os textos

## 🛠️ Exemplo Python

```python
import zipfile
import os

with zipfile.ZipFile("prompts.zip", "r") as zip_ref:
    zip_ref.extractall("conteudo_prompts")

for root, dirs, files in os.walk("conteudo_prompts"):
    for file in files:
        if file.endswith(".txt"):
            with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                conteudo = f.read()
                print(f"Arquivo {file}:
{conteudo[:200]}...
")
```

## 🔒 Boas Práticas

- Use UTF-8
- Valide antes de publicar
- Adicione timestamp aos arquivos salvos
