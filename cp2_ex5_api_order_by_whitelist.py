"""
exercicio 5 - o order by que o %s nao protege

%s so parametriza valor de dado, nao nome de coluna. pra ordenar
dinamico sem abrir injecao, usa uma whitelist fechada de colunas
"""

import os

import mysql.connector
from flask import Flask, jsonify, request

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

# mapa fechado: so essas chaves existem pro cliente, o valor e o nome
# real da coluna. o cliente nunca escreve o nome da coluna direto na query
COLUNAS = {"data": "criado_em", "sev": "severidade", "ip": "ip_origem"}
ORDEM = {"asc": "ASC", "desc": "DESC"}
TAMANHO_MAXIMO = 100

app = Flask(__name__)


def conectar():
    return mysql.connector.connect(**DB_CONFIG)


def preparar_tabela():
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS eventos (
            id INT AUTO_INCREMENT PRIMARY KEY,
            ip_origem VARCHAR(45) NOT NULL,
            severidade VARCHAR(20) NOT NULL,
            criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("SELECT COUNT(*) FROM eventos")
    if cur.fetchone()[0] == 0:
        dados = [
            ("185.220.101.1", "critica"), ("91.240.118.172", "alta"), ("45.33.32.156", "media"),
            ("192.168.1.10", "baixa"), ("185.220.101.1", "alta"), ("91.240.118.172", "critica"),
        ]
        cur.executemany("INSERT INTO eventos (ip_origem, severidade) VALUES (%s, %s)", dados)
    conn.commit()
    cur.close()
    conn.close()


@app.route("/api/eventos")
def listar_eventos():
    ordenar_por = request.args.get("ordenar_por", "data")
    ordem = request.args.get("ordem", "desc")
    tamanho_raw = request.args.get("tamanho", "20")

    if ordenar_por not in COLUNAS:
        return jsonify({"erro": "campo de ordenacao invalido"}), 400
    if ordem not in ORDEM:
        return jsonify({"erro": "ordem invalida"}), 400
    if not tamanho_raw.isdigit():
        return jsonify({"erro": "tamanho deve ser inteiro"}), 400

    tamanho = min(int(tamanho_raw), TAMANHO_MAXIMO)
    coluna_sql = COLUNAS[ordenar_por]
    ordem_sql = ORDEM[ordem]

    # coluna e ordem vem da whitelist acima, nunca do request direto.
    # so o valor de tamanho e' parametro real de query (%s)
    conn = conectar()
    cur = conn.cursor(dictionary=True)
    query = f"SELECT * FROM eventos ORDER BY {coluna_sql} {ordem_sql} LIMIT %s"
    cur.execute(query, (tamanho,))
    resultado = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify(resultado), 200


# %s vira um valor escapado dentro da query (um literal), o driver sabe
# que aquilo e' dado. ORDER BY %s tentaria colocar um literal onde o sql
# espera um identificador de coluna, o que ou quebra a sintaxe ou (pior,
# dependendo do driver) e silenciosamente ignorado, por isso identificador
# de coluna so pode vir de uma lista fechada no codigo, nunca de parametro


if __name__ == "__main__":
    preparar_tabela()
    app.run(debug=True, host="0.0.0.0", port=5001)
