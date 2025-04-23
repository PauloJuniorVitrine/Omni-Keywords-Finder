# src/4-keywords/utils/registrar_padroes_efetivos.py

import json
import os
import re
from threading import Lock

APRENDIZADO_PATH = "src/4-keywords/data/aprendizado_keywords.json"
_lock = Lock()

def extrair_operador_modificador(frase: str, tema: str):
    """
    Extrai operador e modificador com base na posição do tema central.
    Exemplo: "como fazer email marketing para iniciantes"
    → operador: "como fazer", modificador: "para iniciantes"
    """
    tema = tema.strip().lower()
    frase = frase.strip().lower()

    if tema not in frase:
        return None, None

    partes = frase.split(tema)
    operador = partes[0].strip() if partes[0].strip() else None
    modificador = partes[1].strip() if len(partes) > 1 and partes[1].strip() else None

    # Remove operadores genéricos inúteis
    if operador and len(operador.split()) <= 1:
        operador = None
    if modificador and len(modificador.split()) <= 1:
        modificador = None

    return operador, modificador

def carregar_aprendizado():
    """
    Lê o JSON de aprendizado. Se estiver corrompido, retorna dicionário vazio.
    """
    if os.path.exists(APRENDIZADO_PATH):
        try:
            with open(APRENDIZADO_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def salvar_aprendizado(dados):
    """
    Salva o JSON atualizado de forma segura com lock.
    """
    os.makedirs(os.path.dirname(APRENDIZADO_PATH), exist_ok=True)

    with _lock:
        try:
            with open(APRENDIZADO_PATH, "w", encoding="utf-8") as f:
                json.dump(dados, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[ERRO] Falha ao salvar aprendizado: {e}")

def registrar_padroes_efetivos(
    tema: str,
    frases_geradas: list,
    frases_coletadas: list,
    silent: bool = True
):
    """
    Atualiza o histórico de aprendizado com base nas frases coletadas com sucesso.
    Mantém contagem de frequência de operadores e modificadores eficazes.
    """

    if not isinstance(tema, str) or not isinstance(frases_geradas, list) or not isinstance(frases_coletadas, list):
        if not silent:
            print("[registrar_padroes_efetivos] Entradas inválidas.")
        return

    tema = tema.strip().lower()
    aprendizado = carregar_aprendizado()

    if tema not in aprendizado:
        aprendizado[tema] = {
            "operadores_efetivos": {},
            "modificadores_efetivos": {}
        }

    operadores_dict = aprendizado[tema]["operadores_efetivos"]
    modificadores_dict = aprendizado[tema]["modificadores_efetivos"]

    for frase in frases_coletadas:
        if frase in frases_geradas:
            operador, modificador = extrair_operador_modificador(frase, tema)

            if operador:
                operadores_dict[operador] = operadores_dict.get(operador, 0) + 1
                if not silent:
                    print(f"[aprendizado] operador ↑ {operador}")

            if modificador:
                modificadores_dict[modificador] = modificadores_dict.get(modificador, 0) + 1
                if not silent:
                    print(f"[aprendizado] modificador ↑ {modificador}")

    # Ordenar os dicionários por frequência
    aprendizado[tema]["operadores_efetivos"] = dict(
        sorted(operadores_dict.items(), key=lambda x: x[1], reverse=True)
    )
    aprendizado[tema]["modificadores_efetivos"] = dict(
        sorted(modificadores_dict.items(), key=lambda x: x[1], reverse=True)
    )

    salvar_aprendizado(aprendizado)
