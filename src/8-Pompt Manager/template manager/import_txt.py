import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from prompt_manager.templates_editor.models import Base, TemplatePrompt, CategoriaSemana
from datetime import datetime
from typing import List

# =============================
# CONFIGURAÇÃO DO BANCO
# =============================
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///prompt_manager.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# =============================
# LOGGING
# =============================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("import_txt")

# =============================
# FUNÇÃO UTILITÁRIA
# =============================
def limpar_texto_prompt(texto: str) -> str:
    return ' '.join(texto.strip().replace("\r", "").split())

# =============================
# IMPORTADOR DE TEMPLATES TXT
# =============================
def importar_templates_txt(diretorio_txt: str, nicho: str, categoria: str, tipo_template: str = "geral"):
    if not os.path.isdir(diretorio_txt):
        logger.error(f"Diretório inválido: {diretorio_txt}")
        return

    try:
        categoria_enum = CategoriaSemana[categoria.capitalize()]
    except KeyError:
        logger.error(f"Categoria inválida: {categoria}")
        return

    arquivos = sorted([f for f in os.listdir(diretorio_txt) if f.endswith(".txt")])
    logger.info(f"🔍 {len(arquivos)} arquivos .txt encontrados no diretório '{diretorio_txt}'.")

    session = SessionLocal()
    adicionados: List[str] = []
    ignorados: List[str] = []

    for idx, arquivo in enumerate(arquivos, start=1):
        caminho = os.path.join(diretorio_txt, arquivo)
        with open(caminho, "r", encoding="utf-8") as f:
            conteudo = f.read()

        conteudo_limpo = limpar_texto_prompt(conteudo)

        if "{{palavra_chave}}" not in conteudo_limpo:
            logger.warning(f"⚠️ Ignorado '{arquivo}' (sem placeholder obrigatório).")
            ignorados.append(arquivo)
            continue

        nome_prompt = f"Prompt {idx:03d} - {categoria.capitalize()} - {nicho}"

        template = TemplatePrompt(
            nome=nome_prompt,
            nicho=nicho,
            categoria=categoria_enum,
            modelo_texto=conteudo_limpo,
            arquivo_origem=arquivo,
            tipo_template=tipo_template,
            descricao=f"Importado em {datetime.utcnow().isoformat()} do arquivo {arquivo}"
        )

        session.add(template)
        adicionados.append(arquivo)

    session.commit()
    session.close()

    logger.info(f"✅ {len(adicionados)} templates importados com sucesso.")
    if ignorados:
        logger.info(f"⚠️ {len(ignorados)} arquivos ignorados por falta de placeholder.")
    for nome in adicionados:
        logger.debug(f"✔️ Importado: {nome}")
    for nome in ignorados:
        logger.debug(f"⏭️ Ignorado: {nome}")


# =============================
# EXEMPLO DE USO
# =============================
if __name__ == "__main__":
    importar_templates_txt(
        diretorio_txt="templates_txt",
        nicho="Marketing",
        categoria="Segunda",
        tipo_template="post"
    )
