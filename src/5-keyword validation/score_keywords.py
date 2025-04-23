import logging
from typing import Optional, Union

logger = logging.getLogger("score_keywords")
logging.basicConfig(level=logging.INFO)

def calcular_score(
    volume: int,
    cpc: float,
    config: Optional[dict] = None,
    detalhado: bool = False,
    trace_id: Optional[str] = None
) -> Union[float, dict]:
    """
    Calcula o score final de uma palavra-chave com base no volume de busca e no CPC estimado.
    Permite configuração de pesos e retorno detalhado.

    :param volume: Volume de busca mensal estimado (deve ser >= 0)
    :param cpc: Custo por clique médio estimado (deve ser >= 0)
    :param config: Dicionário com 'peso_volume' e 'peso_cpc'
    :param detalhado: Se True, retorna dicionário com contribuições individuais
    :param trace_id: ID opcional para logging rastreável
    :return: Score final ou dicionário detalhado
    """
    if volume < 0 or cpc < 0:
        raise ValueError("Volume e CPC devem ser valores não-negativos.")

    peso_volume = config.get('peso_volume', 0.5) if config else 0.5
    peso_cpc = config.get('peso_cpc', 0.5) if config else 0.5

    contrib_volume = volume * peso_volume
    contrib_cpc = cpc * peso_cpc * 100
    score = round(contrib_volume + contrib_cpc, 2)

    if trace_id:
        logger.debug(f"[{trace_id}] Score={score} | V={volume}*{peso_volume} + C={cpc}*{peso_cpc}*100")

    if detalhado:
        return {
            "score": score,
            "volume_contrib": round(contrib_volume, 2),
            "cpc_contrib": round(contrib_cpc, 2),
            "peso_volume": peso_volume,
            "peso_cpc": peso_cpc
        }

    return score

# =============================
# EXEMPLO DE USO
# =============================
if __name__ == "__main__":
    config = {"peso_volume": 0.6, "peso_cpc": 0.4}
    resultado = calcular_score(1200, 1.75, config=config, detalhado=True, trace_id="demo-123")
    print("Resultado detalhado:", resultado)
