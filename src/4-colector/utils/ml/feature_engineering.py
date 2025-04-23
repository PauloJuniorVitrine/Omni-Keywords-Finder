# src/ml/feature_engineering.py

import re
import string
import unicodedata
import spacy
import numpy as np
from typing import TypedDict

# Carrega modelo spaCy
nlp = spacy.load("pt_core_news_sm")

# Lista de palavras modificadoras
MODIFICADORES = ["melhor", "mais barato", "top", "2024", "em promoção", "funcional"]

# ---- TypedDict para padronizar saída ----
class FeaturesDict(TypedDict):
    qtde_palavras: int
    contagem_caracteres: int
    contem_ano: int
    qtde_entidades: int
    contem_modificadores: int
    tema_igual: int
    origem: str
    qtde_tags: int
    embedding_300d: list[float]  # Vetor semântico opcional

# ---- Normalização reutilizável ----
def normalizar_texto(texto):
    texto = texto.lower().strip()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("utf-8")
    texto = texto.translate(str.maketrans("", "", string.punctuation))
    return texto

# ---- Contadores auxiliares ----
def contar_entidades(texto):
    doc = nlp(texto)
    return len(doc.ents)

def contem_modificadores(texto):
    texto_normalizado = normalizar_texto(texto)
    return int(any(mod in texto_normalizado for mod in MODIFICADORES))

# ---- Função principal ----
def extrair_features(texto: str, tema: str, origem: str, tags: list[str], debug: bool = False) -> FeaturesDict:
    texto_norm = normalizar_texto(texto)
    tema_norm = normalizar_texto(tema)
    doc = nlp(texto_norm)

    features: FeaturesDict = {
        "qtde_palavras": len(texto_norm.split()),
        "contagem_caracteres": len(texto_norm),
        "contem_ano": int(bool(re.search(r"\b20\d{2}\b", texto_norm))),
        "qtde_entidades": len(doc.ents),
        "contem_modificadores": contem_modificadores(texto),
        "tema_igual": int(texto_norm == tema_norm),
        "origem": origem.lower(),
        "qtde_tags": len(tags),
        "embedding_300d": doc.vector[:300].tolist()  # Vetor semântico truncado
    }

    if debug:
        print(f"[DEBUG] Features extraídas para '{texto}':\n{features}")

    return features

# ---- Validador para produção ----
def validar_features(features: dict) -> bool:
    chaves_esperadas = {
        "qtde_palavras", "contagem_caracteres", "contem_ano", "qtde_entidades",
        "contem_modificadores", "tema_igual", "origem", "qtde_tags", "embedding_300d"
    }
    if not all(k in features for k in chaves_esperadas):
        return False
    if not isinstance(features["embedding_300d"], list) or len(features["embedding_300d"]) < 100:
        return False
    return True
