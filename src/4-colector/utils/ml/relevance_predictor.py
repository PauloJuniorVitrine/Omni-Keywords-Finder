# src/ml/relevance_predictor.py

import joblib
import os
import numpy as np
import logging
from typing import Tuple, Optional
from ml.feature_engineering import extrair_features, validar_features

# Configuração de logging estruturado e níveis customizados
logger = logging.getLogger("relevance_predictor")
handler = logging.StreamHandler()
formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

# Caminho padrão do modelo treinado (pode ser sobrescrito via ENV ou config externa futuramente)
MODELO_PATH = os.getenv("MODELO_RELEVANCIA_PATH", "src/ml/modelo_relevancia.pkl")

class RelevancePredictor:
    def __init__(self, modelo_path: str = MODELO_PATH):
        self.modelo_path = modelo_path
        self.modelo = self._carregar_modelo()

    def _carregar_modelo(self):
        if not os.path.exists(self.modelo_path):
            logger.warning(f"⚠️ Modelo não encontrado em: {self.modelo_path}")
            return None
        try:
            modelo = joblib.load(self.modelo_path)
            logger.info(f"✅ Modelo carregado de: {self.modelo_path}")
            return modelo
        except Exception as e:
            logger.error(f"Erro ao carregar modelo: {e}", exc_info=True)
            return None

    def prever(self, texto: str, tema: str, origem: str, tags: list[str], debug: bool = False, threshold: float = 0.5) -> Tuple[bool, float]:
        """
        Realiza a predição de relevância de uma sugestão com base no modelo treinado.

        Retorna:
        - valido (bool): se a sugestão é considerada relevante
        - escore (float): probabilidade de relevância
        """
        if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
            logger.error("❌ As tags devem ser uma lista de strings.")
            raise ValueError("As tags devem ser uma lista de strings.")

        try:
            features = extrair_features(texto, tema, origem, tags, debug=debug)
        except Exception as e:
            logger.error(f"Erro na extração de features: {e}", exc_info=True)
            return False, 0.0

        if not validar_features(features):
            logger.warning(f"⚠️ Features inválidas para texto='{texto}' | tema='{tema}'")
            return False, 0.0

        if self.modelo is None:
            logger.warning("⚠️ Modelo indisponível. Retornando escore neutro.")
            return False, 0.0

        try:
            X_base = [features[k] for k in features if k != "embedding_300d"]
            X_emb = features["embedding_300d"]
            X_input = np.array([X_base + X_emb])

            prob = self.modelo.predict_proba(X_input)[0][1]
            valido = prob >= threshold

            logger.info(f"📊 Predição: texto='{texto[:30]}...' | escore={prob:.4f} | relevante={valido}")

            if debug:
                logger.debug("\n[DEBUG] --- Predição de Relevância ---")
                logger.debug(f"Texto: {texto}")
                logger.debug(f"Tema: {tema}")
                logger.debug(f"Origem: {origem}")
                logger.debug(f"Tags: {tags}")
                logger.debug(f"Escore: {prob:.4f} | Relevante: {valido}\n")

            return valido, float(prob)

        except Exception as e:
            logger.error(f"Erro ao realizar predição: {e}", exc_info=True)
            return False, 0.0

# Interface funcional para uso legado ou simples
_default_predictor: Optional[RelevancePredictor] = None

def prever_relevancia(texto: str, tema: str, origem: str, tags: list[str], debug: bool = False, threshold: float = 0.5) -> Tuple[bool, float]:
    global _default_predictor
    if _default_predictor is None:
        _default_predictor = RelevancePredictor()
    return _default_predictor.prever(texto, tema, origem, tags, debug, threshold)
