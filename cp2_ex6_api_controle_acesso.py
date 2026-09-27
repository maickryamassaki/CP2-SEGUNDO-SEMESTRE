"""
exercicio 6 - controle de acesso quebrado

cada analista so ve os proprios incidentes, so nivel >= 5 apaga
qualquer um. autenticacao por header x-api-key validado no mysql
"""

import os

import mysql.connector
from flask import Flask, g, jsonify, request

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

app = Flask(__name__)


def conectar():
    return mysql.connector.connect(**DB_CONFIG)


def preparar_tabelas():
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS analistas (
            id INT PRIMARY KEY, nome VARCHAR(50), api_key VARCHAR(50) UNIQUE, nivel INT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS incidentes (
            id INT PRIMARY KEY, dono_id INT, titulo VARCHAR(100), severidade VARCHAR(20), status VARCHAR(20) DEFAULT 'aberto'
        )
    """)
    cur.execute("DELETE FROM incidentes")
    cur.execute("DELETE FROM analistas")
    cur.executemany("INSERT INTO analistas (id, nome, api_key, nivel) VALUES (%s, %s, %s, %s)",
                     [(1, "ana", "key-ana-001", 5), (2, "bruno", "key-bruno-002", 2)])
    cur.executemany("INSERT INTO incidentes (id, dono_id, titulo, severidade) VALUES (%s, %s, %s, %s)",
                     [(1, 1, "Brute force SSH", "critica"), (2, 2, "Phishing no RH", "media")])
    conn.commit()
    cur.close()
    conn.close()


def autenticar():
    """valida o header x-api-key no mysql, guarda o analista em g.analista.
    retorna None se autenticado, ou a resposta de erro pronta caso contrario"""
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return jsonify({"erro": "credencial ausente"}), 401

    conn = conectar()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, nome, nivel FROM analistas WHERE api_key = %s", (api_key,))
    analista = cur.fetchone()
    cur.close()
    conn.close()

    if analista is None:
        return jsonify({"erro": "credencial invalida"}), 401

    g.analista = analista
    return None


@app.route("/api/incidentes/<int:incidente_id>")
def buscar_incidente(incidente_id):
    erro = autenticar()
    if erro:
        return erro

    conn = conectar()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM incidentes WHERE id = %s", (incidente_id,))
    incidente = cur.fetchone()
    cur.close()
    conn.close()

    if incidente is None:
        return jsonify({"erro": "nao encontrado"}), 404

    # idor: dono do incidente ou nivel alto, senao 403 generico sem
    # dizer se o incidente existe ou nao
    if incidente["dono_id"] != g.analista["id"] and g.analista["nivel"] < 5:
        return jsonify({"erro": "acesso negado"}), 403

    return jsonify(incidente), 200


@app.route("/api/incidentes")
def listar_incidentes():
    erro = autenticar()
    if erro:
        return erro

    conn = conectar()
    cur = conn.cursor(dictionary=True)
    if g.analista["nivel"] >= 5:
        cur.execute("SELECT * FROM incidentes")
    else:
        cur.execute("SELECT * FROM incidentes WHERE dono_id = %s", (g.analista["id"],))
    resultado = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(resultado), 200


@app.route("/api/incidentes/<int:incidente_id>", methods=["DELETE"])
def remover_incidente(incidente_id):
    erro = autenticar()
    if erro:
        return erro

    if g.analista["nivel"] < 5:
        return jsonify({"erro": "acesso negado"}), 403

    conn = conectar()
    cur = conn.cursor()
    cur.execute("DELETE FROM incidentes WHERE id = %s", (incidente_id,))
    conn.commit()
    apagado = cur.rowcount > 0
    cur.close()
    conn.close()

    if not apagado:
        return jsonify({"erro": "nao encontrado"}), 404
    return jsonify({"removido": incidente_id}), 200


if __name__ == "__main__":
    preparar_tabelas()
    app.run(debug=True, host="0.0.0.0", port=5002)
