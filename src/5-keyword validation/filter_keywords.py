from typing import List, Dict


def filtrar_keywords(
    lista: List[Dict],
    concorrencia_aceita: List[str] = ["baixa", "média"],
    palavras_excluidas: List[str] = [],
    volume_min: int = 100,
    score_min: float = 1000.0
) -> List[Dict]:
    """
    Aplica filtros adicionais sobre palavras validadas:
    - Concorrência aceita: baixa ou média (por padrão)
    - Palavras a excluir por termo
    - Volume mínimo de busca
    - Score mínimo

    :param lista: Lista de palavras validadas (dicionários)
    :param concorrencia_aceita: Lista com níveis de concorrência aceitos
    :param palavras_excluidas: Lista de substrings a excluir
    :param volume_min: Filtro por volume
    :param score_min: Filtro por score
    :return: Lista de palavras após filtro
    """
    filtradas = []
    for item in lista:
        if item['concorrencia'] not in concorrencia_aceita:
            continue

        if any(substr.lower() in item['palavra'].lower() for substr in palavras_excluidas):
            continue

        if item['volume'] < volume_min:
            continue

        if item['score_final'] < score_min:
            continue

        filtradas.append(item)

    return filtradas


# =============================
# EXEMPLO DE USO
# =============================
if __name__ == "__main__":
    palavras = [
        {"palavra": "dicas marketing", "volume": 1200, "score_final": 1400, "concorrencia": "baixa"},
        {"palavra": "curso grátis", "volume": 900, "score_final": 1300, "concorrencia": "alta"},
        {"palavra": "estratégia vendas", "volume": 800, "score_final": 900, "concorrencia": "média"}
    ]

    resultado = filtrar_keywords(
        palavras,
        concorrencia_aceita=["baixa", "média"],
        palavras_excluidas=["grátis"],
        volume_min=1000,
        score_min=1000
    )

    for r in resultado:
        print(r)
