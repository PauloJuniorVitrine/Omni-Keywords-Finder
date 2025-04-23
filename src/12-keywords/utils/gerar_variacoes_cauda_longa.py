# src/4-keywords/utils/gerar_variacoes_cauda_longa.py

import unicodedata
import re
import json
import os
from functools import lru_cache

APRENDIZADO_PATH = "src/4-keywords/data/aprendizado_keywords.json"

def limpar_texto(texto: str) -> str:
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8')
    texto = re.sub(r'\s+', ' ', texto)
    texto = re.sub(r'[^\w\s]', '', texto)
    return texto.strip().lower()

def carregar_aprendizado() -> dict:
    if os.path.exists(APRENDIZADO_PATH):
        try:
            with open(APRENDIZADO_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def reordenar_por_aprendizado(padrao_default: list, aprendizado_dict: dict) -> list:
    priorizados = list(aprendizado_dict.keys())
    return priorizados + [p for p in padrao_default if p not in priorizados]

def gerar_frases(tema: str, operadores: list, modificadores: list) -> set:
    """
    Gera todas as combinações possíveis: operador + tema, tema + modificador, operador + tema + modificador
    """
    variacoes = set()

    for operador in operadores:
        variacoes.add(f"{operador} {tema}")

    for modificador in modificadores:
        variacoes.add(f"{tema} {modificador}")

    for operador in operadores:
        for modificador in modificadores:
            variacoes.add(f"{operador} {tema} {modificador}")

    return variacoes

@lru_cache(maxsize=128)
def gerar_variacoes_cauda_longa(
    tema: str,
    operadores_intencao_default: tuple = (
        "como fazer", "o que é", "para que serve", "exemplos de",
        "vantagens do", "passo a passo de", "melhores estratégias de",
        "dicas de", "como funciona", "por que usar", "segredos do"
    ),
    modificadores_default: tuple = (
        "para iniciantes", "com resultados", "passo a passo", "gratuito",
        "rápido", "eficiente", "sem gastar muito", "com alta conversão"
    ),
    tamanho_minimo: int = 3,
    ordenar: bool = True,
    usar_aprendizado: bool = True,
    debug: bool = False
) -> list:
    """
    Gera variações long tail para um tema, com aprendizado adaptativo, priorização e filtragem semântica.
    """

    if not tema or not isinstance(tema, str):
        return []

    tema = limpar_texto(tema)

    operadores_intencao = list(operadores_intencao_default)
    modificadores = list(modificadores_default)

    if usar_aprendizado:
        aprendizado = carregar_aprendizado()
        dados = aprendizado.get(tema, {})
        operadores_aprendidos = dados.get("operadores_efetivos", {})
        modificadores_aprendidos = dados.get("modificadores_efetivos", {})

        operadores_intencao = reordenar_por_aprendizado(operadores_intencao, operadores_aprendidos)
        modificadores = reordenar_por_aprendizado(modificadores, modificadores_aprendidos)

        if debug:
            print(f"[debug] Operadores priorizados: {operadores_intencao[:3]}")
            print(f"[debug] Modificadores priorizados: {modificadores[:3]}")

    frases = gerar_frases(tema, operadores_intencao, modificadores)

    # Filtro: somente frases long tail reais
    long_tails = [f for f in frases if len(f.split()) >= tamanho_minimo]

    # Deduplicação avançada: evitar combinações estruturalmente redundantes (ex: "passo a passo de tema", "tema passo a passo")
    vistos = set()
    final = []
    for frase in long_tails:
        chave = tuple(sorted(frase.split()))
        if chave not in vistos:
            vistos.add(chave)
            final.append(frase)

    if ordenar:
        final = sorted(final, key=lambda f: (len(f.split()), f))

    return final
