"""
prepara o banco 'seguranca' usado pelo app_vulneravel.py e pelo
app_seguro.py. roda isso uma vez antes de testar os dois
"""

import os

import mysql.connector

MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD")
if not MYSQL_PASSWORD:
    raise RuntimeError("defina a variavel de ambiente MYSQL_PASSWORD antes de rodar")

conn = mysql.connector.connect(
    host=os.getenv("MYSQL_HOST", "localhost"),
    port=int(os.getenv("MYSQL_PORT", "3306")),
    user=os.getenv("MYSQL_USER", "root"),
    password=MYSQL_PASSWORD,
)
cur = conn.cursor()
cur.execute("CREATE DATABASE IF NOT EXISTS seguranca")
cur.execute("USE seguranca")
cur.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nome VARCHAR(50) NOT NULL,
        email VARCHAR(100) NOT NULL,
        senha VARCHAR(100) NOT NULL
    )
""")
cur.execute("DELETE FROM usuarios")
cur.executemany(
    "INSERT INTO usuarios (nome, email, senha) VALUES (%s, %s, %s)",
    [("admin", "admin@x.com", "hash_admin_aqui"), ("ana", "ana@x.com", "hash_ana_aqui"), ("bruno", "bruno@x.com", "hash_bruno_aqui")],
)
conn.commit()
cur.close()
conn.close()
print("banco seguranca pronto, tabela usuarios populada com 3 registros")
