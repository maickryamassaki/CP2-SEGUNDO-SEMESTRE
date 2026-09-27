"""
exercicio 2 - migracao relacional para documentos

le ativos + alertas normalizados no mysql via join, monta documentos
aninhados e insere no mongodb, depois prova que nada se perdeu
"""

import os

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


def preparar_mysql(conn):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ativos (
            id INT PRIMARY KEY,
            nome VARCHAR(50) NOT NULL,
            ip VARCHAR(45) NOT NULL UNIQUE,
            criticidade ENUM('baixa', 'media', 'alta') NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS alertas (
            id INT PRIMARY KEY,
            ativo_id INT NOT NULL,
            tipo VARCHAR(50) NOT NULL,
            severidade VARCHAR(20) NOT NULL,
            criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ativo_id) REFERENCES ativos(id)
        )
    """)
    cur.execute("DELETE FROM alertas")
    cur.execute("DELETE FROM ativos")

    ativos = [(1, "SRV-WEB01", "192.168.1.10", "alta"), (2, "PC-RH03", "192.168.1.45", "baixa")]
    alertas = [(1, 1, "BRUTE_FORCE", "critica"), (2, 1, "PORT_SCAN", "alta"), (3, 2, "XSS", "media")]

    cur.executemany("INSERT INTO ativos (id, nome, ip, criticidade) VALUES (%s, %s, %s, %s)", ativos)
    cur.executemany("INSERT INTO alertas (id, ativo_id, tipo, severidade) VALUES (%s, %s, %s, %s)", alertas)
    conn.commit()
    cur.close()


def ler_alertas_com_join(conn):
    # join parametrizado (aqui nao tem parametro de usuario, mas o padrao
    # continua sendo cursor parametrizado, nunca string concatenada)
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT alertas.tipo, alertas.severidade,
               ativos.nome, ativos.ip, ativos.criticidade
        FROM alertas
        JOIN ativos ON ativos.id = alertas.ativo_id
    """)
    linhas = cur.fetchall()
    cur.close()
    return linhas


def montar_documentos(linhas):
    documentos = []
    for linha in linhas:
        documentos.append({
            "tipo": linha["tipo"],
            "severidade": linha["severidade"],
            "ativo": {
                "nome": linha["nome"],
                "ip": linha["ip"],
                "criticidade": linha["criticidade"],
            },
        })
    return documentos


def main():
    conn = mysql.connector.connect(**DB_CONFIG)
    preparar_mysql(conn)

    linhas = ler_alertas_com_join(conn)
    documentos = montar_documentos(linhas)

    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    db = client[os.getenv("MONGO_DATABASE", "cp2_bd")]
    col = db["alertas"]
    col.delete_many({})
    col.insert_many(documentos)

    total_mysql = len(linhas)
    total_mongo = col.count_documents({})
    status = "MIGRACAO INTEGRA" if total_mysql == total_mongo else "DIVERGENCIA"
    print(f"MySQL: {total_mysql} alertas | MongoDB: {total_mongo} documentos -> {status}")

    alta_criticidade = col.count_documents({"ativo.criticidade": "alta"})
    print(f"Consulta sem JOIN: db.alertas.find({{'ativo.criticidade':'alta'}}) -> {alta_criticidade} documentos")

    

    conn.close()
    client.close()


if __name__ == "__main__":
    main()
