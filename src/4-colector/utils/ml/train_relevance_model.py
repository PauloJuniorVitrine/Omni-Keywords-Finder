# src/ml/train_relevance_model.py

import pandas as pd
import joblib
import json
from pathlib import Path
from datetime import datetime

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, GridSearchCV, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, accuracy_score

from ml.feature_engineering import extrair_features, validar_features

# ---- Configuração ----
DATASET_PATH = "data/palavras_rotuladas.jsonl"
MODELO_SAIDA_PATH = "src/ml/modelo_relevancia.pkl"
METRICAS_SAIDA_PATH = "src/ml/metricas_relevancia.json"

# ---- Carregamento dos dados rotulados ----
def carregar_dados_rotulados():
    registros = []
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        for linha in f:
            dado = json.loads(linha)
            features = extrair_features(
                texto=dado["texto"],
                tema=dado["tema"],
                origem=dado.get("origem", "desconhecida"),
                tags=dado.get("tags", [])
            )
            if validar_features(features):
                features["label"] = int(dado["relevante"])
                registros.append(features)
    return pd.DataFrame(registros)

# ---- Treinamento do modelo ----
def treinar_modelo(df: pd.DataFrame):
    X = df.drop(columns=["label", "origem", "embedding_300d"])
    X_emb = pd.DataFrame(df["embedding_300d"].tolist())
    X_total = pd.concat([X.reset_index(drop=True), X_emb], axis=1)
    y = df["label"]

    X_train, X_test, y_train, y_test = train_test_split(X_total, y, test_size=0.2, random_state=42)

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", RandomForestClassifier(random_state=42))
    ])

    param_grid = {
        "clf__n_estimators": [50, 100, 200],
        "clf__max_depth": [None, 10, 20]
    }

    grid = GridSearchCV(pipeline, param_grid, cv=5, n_jobs=-1)
    grid.fit(X_train, y_train)

    preds = grid.predict(X_test)
    print("\nRelatório de Classificação:\n", classification_report(y_test, preds))
    print("Acurácia:", accuracy_score(y_test, preds))

    scores = cross_val_score(grid.best_estimator_, X_total, y, cv=5)
    print("Validação cruzada (CV=5):", scores)
    print("Média CV:", scores.mean())

    # ---- Salvar modelo treinado ----
    Path(MODELO_SAIDA_PATH).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(grid.best_estimator_, MODELO_SAIDA_PATH)
    print(f"\n✅ Modelo salvo em: {MODELO_SAIDA_PATH}")

    # ---- Salvar métricas e parâmetros em JSON ----
    metricas = {
        "modelo": "RandomForest",
        "versao": "v1.0.0",
        "data_treino": datetime.now().isoformat(),
        "acuracia": accuracy_score(y_test, preds),
        "media_cv": scores.mean(),
        "params_otimizados": grid.best_params_,
        "features": list(X.columns) + [f"embed_{i}" for i in range(X_emb.shape[1])]
    }
    with open(METRICAS_SAIDA_PATH, "w", encoding="utf-8") as f:
        json.dump(metricas, f, indent=2)
    print(f"📊 Métricas salvas em: {METRICAS_SAIDA_PATH}")

if __name__ == "__main__":
    df = carregar_dados_rotulados()
    if df.empty:
        print("⚠️ Nenhum dado válido encontrado para treino.")
    else:
        treinar_modelo(df)
