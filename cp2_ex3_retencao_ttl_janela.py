"""
exercicio 3 - retencao e janela temporal

cria a colecao eventos com indice ttl, gera 200 eventos espalhados
nas ultimas 24h e mostra a distribuicao de falhas por hora
"""

import os
import random
from datetime import datetime, timedelta, timezone

from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
random.seed(42)


def gerar_eventos(quantidade=200):
    agora = datetime.now(timezone.utc)
    eventos = []
    for _ in range(quantidade):
        minutos_atras = random.randint(0, 24 * 60 - 1)
        eventos.append({
            "tipo": "FAIL",
            "ip": random.choice(["185.220.101.1", "91.240.118.172", "45.33.32.156", "192.168.1.10"]),
            "timestamp": agora - timedelta(minutes=minutos_atras),
        })
    return eventos


def main():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    db = client[os.getenv("MONGO_DATABASE", "cp2_bd")]
    col = db["eventos"]
    col.drop()

    # ttl: qualquer documento com mais de 7 dias some sozinho, o campo do
    # indice precisa ser um datetime de verdade, nao string
    col.create_index("timestamp", expireAfterSeconds=604800)

    eventos = gerar_eventos(200)
    col.insert_many(eventos)

    pipeline = [
        {"$group": {"_id": {"$hour": "$timestamp"}, "total": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    distribuicao = list(col.aggregate(pipeline))

    print("=== Falhas por hora (ultimas 24h) ===")
    pico_hora, pico_total = None, -1
    for doc in distribuicao:
        hora, total = doc["_id"], doc["total"]
        barra = "\u2588" * (total // 2 or 1)
        marca = "  <- pico" if total > pico_total else ""
        if total > pico_total:
            pico_hora, pico_total = hora, total
        print(f"{hora:02d}h | {barra} {total}{marca}")

    print(f"\nHora de pico: {pico_hora:02d}h ({pico_total} falhas)")
    print("Indice TTL ativo: eventos com mais de 7 dias serao removidos automaticamente.")

 

    client.close()


if __name__ == "__main__":
    main()