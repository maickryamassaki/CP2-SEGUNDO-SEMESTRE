"""
exercicio 9 - limitacao de taxa guiada por anomalia

registra cada requisicao, extrai por agregacao o comportamento de
cada ip e usa isolationforest pra decidir quem toma 429
"""

import os
import time
from datetime import datetime, timedelta, timezone

from flask import Flask, jsonify, request
from pymongo import MongoClient
from sklearn.ensemble import IsolationForest

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
JANELA_MINUTOS = 1

app = Flask(__name__)

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
acessos = client[os.getenv("MONGO_DATABASE", "cp2_bd")]["acessos"]

bloqueados = set()  # cache em memoria pra nao rodar o modelo a cada request


def ip_do_cliente():
   
    return request.headers.get("X-Forwarded-For", request.remote_addr)


@app.before_request
def registrar_inicio():
    ip = ip_do_cliente()
    if ip in bloqueados:
        return jsonify({"erro": "muitas requisicoes"}), 429, {"Retry-After": "60"}

    request._acesso_doc = {
        "ip": ip,
        "rota": request.path,
        "metodo": request.method,
        "timestamp": datetime.now(timezone.utc),
    }


@app.after_request
def registrar_fim(response):
    doc = getattr(request, "_acesso_doc", None)
    if doc is not None:
        doc["status"] = response.status_code
        acessos.insert_one(doc)
    return response


def analisar_e_bloquear():
    """roda a analise de anomalia sobre a janela recente e marca ips
    suspeitos pra bloqueio nas proximas requisicoes"""
    desde = datetime.now(timezone.utc) - timedelta(minutes=JANELA_MINUTOS)
    pipeline = [
        {"$match": {"timestamp": {"$gte": desde}}},
        {"$group": {
            "_id": "$ip",
            "total": {"$sum": 1},
            "erros_4xx": {"$sum": {"$cond": [{"$and": [{"$gte": ["$status", 400]}, {"$lt": ["$status", 500]}]}, 1, 0]}},
            "rotas": {"$addToSet": "$rota"},
        }},
    ]
    grupos = list(acessos.aggregate(pipeline))
    if len(grupos) < 2:
        return []

    linhas = []
    for g in grupos:
        req_por_min = g["total"] / JANELA_MINUTOS
        taxa_4xx = g["erros_4xx"] / g["total"]
        rotas_distintas = len(g["rotas"])
        linhas.append((g["_id"], req_por_min, taxa_4xx, rotas_distintas))

    X = [[l[1], l[2], l[3]] for l in linhas]
    modelo = IsolationForest(contamination=0.2, random_state=42)
    predicoes = modelo.fit_predict(X)

    print("=== Analise de acessos ===")
    novos_bloqueados = []
    for (ip, req_min, taxa_4xx, rotas), pred in zip(linhas, predicoes):
        status = "ANOMALIA -> bloqueado" if pred == -1 else "normal"
        print(f"{ip:16s} [{req_min:6.1f} req/min | 4xx {taxa_4xx:.2f} | {rotas} rotas]  -> {status}")
        if pred == -1:
            bloqueados.add(ip)
            novos_bloqueados.append(ip)
    return novos_bloqueados


@app.route("/api/analisar", methods=["POST"])
def analisar():
    novos = analisar_e_bloquear()
    return jsonify({"bloqueados": novos}), 200


@app.route("/api/incidentes")
def rota_de_teste():
    return jsonify({"ok": True}), 200



if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5005)