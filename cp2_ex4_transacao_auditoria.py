"""
exercicio 4 - transacao com trilha de auditoria

so grava a alteracao de nivel se tudo der certo, mas registra toda
tentativa (aceita ou recusada) na trilha de auditoria no mongodb
"""

import os
from datetime import datetime, timezone

import mysql.connector
from pymongo import MongoClient

MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD")
if not MYSQL_PASSWORD:
    raise RuntimeError("defina a variavel de ambiente MYSQL_PASSWORD antes de rodar")

DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": MYSQL_PASSWORD,
    "database": os.getenv("MYSQL_DATABASE", "cp2_bd"),
}
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")

mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
auditoria = mongo_client[os.getenv("MONGO_DATABASE", "cp2_bd")]["auditoria"]


def preparar_mysql(conn):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INT PRIMARY KEY,
            nome VARCHAR(50) NOT NULL,
            email VARCHAR(100) NOT NULL,
            nivel_acesso INT NOT NULL
        )
    """)
    cur.execute("DELETE FROM usuarios")
    usuarios = [(1, "ana", "ana@x.com", 5), (2, "bruno", "bruno@x.com", 2), (3, "caio", "caio@x.com", 1)]
    cur.executemany("INSERT INTO usuarios (id, nome, email, nivel_acesso) VALUES (%s, %s, %s, %s)", usuarios)
    conn.commit()
    cur.close()
    auditoria.delete_many({})


def registrar_auditoria(admin_id, alvo_id, nivel_anterior, nivel_novo, resultado):
    auditoria.insert_one({
        "quem": admin_id,
        "alvo": alvo_id,
        "nivel_anterior": nivel_anterior,
        "nivel_novo": nivel_novo,
        "resultado": resultado,
        "timestamp": datetime.now(timezone.utc),
    })


def alterar_nivel(conn, admin_id, alvo_id, novo_nivel):
    cur = conn.cursor()
    try:
        # ninguem se auto-promove
        if admin_id == alvo_id:
            registrar_auditoria(admin_id, alvo_id, None, novo_nivel, "RECUSADO")
            return False, "auto-promocao"

        cur.execute("SELECT nivel_acesso FROM usuarios WHERE id = %s", (admin_id,))
        row_admin = cur.fetchone()
        if row_admin is None or row_admin[0] < 5:
            registrar_auditoria(admin_id, alvo_id, None, novo_nivel, "RECUSADO")
            return False, "admin sem privilegio"

        cur.execute("SELECT nivel_acesso FROM usuarios WHERE id = %s", (alvo_id,))
        row_alvo = cur.fetchone()
        if row_alvo is None:
            registrar_auditoria(admin_id, alvo_id, None, novo_nivel, "RECUSADO")
            return False, "alvo inexistente"

        nivel_anterior = row_alvo[0]
        cur.execute("UPDATE usuarios SET nivel_acesso = %s WHERE id = %s", (novo_nivel, alvo_id))
        conn.commit()
        registrar_auditoria(admin_id, alvo_id, nivel_anterior, novo_nivel, "OK")
        return True, None
    except mysql.connector.Error as e:
        conn.rollback()
        registrar_auditoria(admin_id, alvo_id, None, novo_nivel, "RECUSADO")
        return False, str(e)
    finally:
        cur.close()


def consultar_nivel(conn, user_id):
    cur = conn.cursor()
    cur.execute("SELECT nivel_acesso FROM usuarios WHERE id = %s", (user_id,))
    row = cur.fetchone()
    cur.close()
    return row[0] if row else None


if __name__ == "__main__":
    conn = mysql.connector.connect(**DB_CONFIG)
    conn.autocommit = False
    preparar_mysql(conn)

    ok, erro = alterar_nivel(conn, 1, 2, 4)
    print(f"alterar_nivel(1, 2, 4) -> {'OK' if ok else 'RECUSADO'}. Bruno: {consultar_nivel(conn, 2)}")

    ok, erro = alterar_nivel(conn, 2, 3, 5)
    print(f"alterar_nivel(2, 3, 5) -> {'OK' if ok else 'RECUSADO'} ({erro}). Caio: {consultar_nivel(conn, 3)}")

    ok, erro = alterar_nivel(conn, 1, 1, 9)
    print(f"alterar_nivel(1, 1, 9) -> {'OK' if ok else 'RECUSADO'} ({erro}). Ana: {consultar_nivel(conn, 1)}")

    ok, erro = alterar_nivel(conn, 1, 99, 3)
    print(f"alterar_nivel(1, 99, 3) -> {'OK' if ok else 'RECUSADO'} ({erro})")

    total = auditoria.count_documents({})
    recusados = auditoria.count_documents({"resultado": "RECUSADO"})
    print(f"\nTrilha de auditoria ao final: {total} documentos")
    print(f"db.auditoria.count_documents({{'resultado':'RECUSADO'}}) -> {recusados}")

    conn.close()
    mongo_client.close()