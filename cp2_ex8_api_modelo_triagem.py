"""
exercicio 8 - modelo de ml servido por api, com metricas auditaveis

a entrada do modelo e' entrada do usuario, entao precisa ser validada
antes de chegar no predict. toda previsao valida vira documento no mongo
"""

import os
from datetime import datetime, timezone

import numpy as np
from flask import Flask, jsonify, request
from pymongo import MongoClient
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
NUM_FEATURES = 4

app = Flask(__name__)

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
previsoes = client[os.getenv("MONGO_DATABASE", "cp2_bd")]["previsoes"]

# features: [falhas_login, portas_distintas, bytes_saida, hora_do_dia]
X = np.array([
    [12, 7, 90000, 3], [10, 6, 70000, 2], [15, 9, 120000, 4], [8, 5, 60000, 1],
    [0, 1, 1200, 14], [1, 1, 900, 10], [0, 2, 1500, 9], [2, 1, 1100, 15],
    [1, 1, 800, 11], [0, 1, 700, 16],
])
y = np.array([1, 1, 1, 1, 0, 0, 0, 0, 0, 0])

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)
modelo = RandomForestClassifier(random_state=42)
modelo.fit(X_train, y_train)

y_pred_teste = modelo.predict(X_test)
METRICAS = {
    "precisao": round(precision_score(y_test, y_pred_teste), 2),
    "recall": round(recall_score(y_test, y_pred_teste), 2),
    "f1": round(f1_score(y_test, y_pred_teste), 2),
    "matriz": confusion_matrix(y_test, y_pred_teste).tolist(),
}


def validar_features(corpo):
    if not corpo or "features" not in corpo:
        return None, "corpo deve conter 'features'"

    features = corpo["features"]
    if not isinstance(features, list) or len(features) != NUM_FEATURES:
        return None, f"esperadas {NUM_FEATURES} features, recebidas {len(features) if isinstance(features, list) else 0}"

    for valor in features:
        if isinstance(valor, bool) or not isinstance(valor, (int, float)):
            return None, "features devem ser numericas"

    return features, None


@app.route("/api/triagem", methods=["POST"])
def triagem():
    corpo = request.get_json(silent=True)
    features, erro = validar_features(corpo)
    if erro:
        return jsonify({"erro": erro}), 400

    entrada = np.array([features])
    predicao = modelo.predict(entrada)[0]
    probabilidades = modelo.predict_proba(entrada)[0]
    confianca = round(float(max(probabilidades)), 2)
    risco = "alto" if predicao == 1 else "baixo"

    previsoes.insert_one({
        "entrada": features,
        "saida": risco,
        "confianca": confianca,
        "timestamp": datetime.now(timezone.utc),
    })

    return jsonify({"risco": risco, "confianca": confianca}), 200


@app.route("/api/modelo/metricas")
def metricas():
    resposta = dict(METRICAS)
    resposta["aviso"] = (
        "acuracia foi omitida de proposito: o conjunto de teste e desbalanceado "
        "(poucos casos de risco alto), entao acuracia alta esconde ataque que "
        "o modelo deixou passar - recall e' a metrica que importa aqui"
    )
    return jsonify(resposta), 200


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5004)