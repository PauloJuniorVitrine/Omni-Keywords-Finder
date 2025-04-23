# google_planner_validator.py
import logging
import random
from typing import List, Optional, TypedDict

from calcular_score import calcular_score

logger = logging.getLogger(__name__)

class PalavraValidada(TypedDict):
    palavra: str
    volume: int
    cpc: float
    concorrencia: str
    score_final: float
    trace_id: str
    tipo: str  # 'primaria', 'secundaria' ou 'suporte'

def validar_com_google_planner(
    palavras: List[str],
    trace_id: Optional[str] = None,
    modo: str = "mock"
) -> List[PalavraValidada]:
    """
    Valida uma lista de palavras-chave utilizando dados do Google Keyword Planner.

    Args:
        palavras (List[str]): Lista de palavras a serem validadas.
        trace_id (Optional[str], optional): ID para rastreamento de logs. Defaults to None.
        modo (str, optional): 'mock' para simulação ou 'api' para integração real. Defaults to "mock".

    Returns:
        List[PalavraValidada]: Lista de palavras com métricas validadas, score final e classificação.
    """
    if not isinstance(palavras, list) or not all(isinstance(p, str) for p in palavras):
        raise ValueError("A entrada 'palavras' deve ser uma lista de strings.")

    trace_id = trace_id or f"trace_{random.randint(1000, 9999)}"
    logger.info(f"[{trace_id}] Iniciando validação de {len(palavras)} palavras (modo={modo})")

    resultados: List[PalavraValidada] = []

    for palavra in palavras:
        if modo == "mock":
            volume = random.randint(100, 10000)
            cpc = round(random.uniform(0.5, 3.5), 2)
            concorrencia = random.choice(["Alta", "Média", "Baixa"])
        else:
            volume = 0
            cpc = 0.0
            concorrencia = "Desconhecida"

        try:
            score = calcular_score(volume, cpc, trace_id=trace_id)
        except Exception as e:
            logger.warning(f"[{trace_id}] Erro ao calcular score para '{palavra}': {e}")
            continue

        resultados.append(PalavraValidada(
            palavra=palavra,
            volume=volume,
            cpc=cpc,
            concorrencia=concorrencia,
            score_final=score,
            trace_id=trace_id,
            tipo="suporte"  # temporário, será ajustado abaixo
        ))

    # Classificação por score_final
    resultados.sort(key=lambda x: x['score_final'], reverse=True)

    for i, resultado in enumerate(resultados):
        if i == 0:
            resultado['tipo'] = 'primaria'
        elif i in (1, 2, 3):
            resultado['tipo'] = 'secundaria'
        else:
            resultado['tipo'] = 'suporte'

    logger.info(f"[{trace_id}] Validação concluída: {len(resultados)} palavras classificadas.")
    return resultados


if __name__ == "__main__":
    palavras_exemplo = ["marketing digital", "SEO local", "automação", "gestão de tráfego", "funil de vendas"]
    validadas = validar_com_google_planner(palavras_exemplo, modo="mock")
    for p in validadas:
        print(p)
