
import logging
import os

import mysql.connector
from flask import Flask, jsonify, request
from markupsafe import escape

MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD")
if not MYSQL_PASSWORD:
    raise RuntimeError("defina a variavel de ambiente MYSQL_PASSWORD antes de rodar")

ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY")
if not ADMIN_API_KEY:
    raise RuntimeError("defina a variavel de ambiente ADMIN_API_KEY antes de rodar")

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("app_seguro")


def db():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        user=os.getenv("MYSQL_USER", "root"),
        password=MYSQL_PASSWORD,
        database=os.getenv("MYSQL_DATABASE", "seguranca"),
    )


@app.after_request
def headers_de_seguranca(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response


@app.errorhandler(Exception)
def erro_generico(e):
    # log completo fica so no servidor, resposta pro cliente nao leva
    # traceback nem nome de tabela nem detalhe de implementacao
    log.exception("erro interno")
    return jsonify({"erro": "erro interno"}), 500


@app.route("/api/usuarios/buscar")
def buscar():
    nome = request.args.get("nome", "")
    conn = db()
    cur = conn.cursor(dictionary=True)
    # consulta parametrizada, sem coluna senha no select
    cur.execute("SELECT id, nome, email FROM usuarios WHERE nome LIKE %s", (f"%{nome}%",))
    resultado = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(resultado)


@app.route("/perfil")
def perfil():
    # escape manual porque a resposta eh construida na mao, nao por template
    nome = escape(request.args.get("u", ""))
    return f"<h1>Bem-vindo, {nome}</h1>"


@app.route("/api/usuarios/<int:uid>", methods=["DELETE"])
def remover(uid):
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return jsonify({"erro": "credencial ausente"}), 401
    if api_key != ADMIN_API_KEY:
        return jsonify({"erro": "acesso negado"}), 403

    conn = db()
    cur = conn.cursor()
    cur.execute("DELETE FROM usuarios WHERE id = %s", (uid,))
    conn.commit()
    apagado = cur.rowcount > 0
    cur.close()
    conn.close()

    log.info(f"usuario {uid} removido via admin")
    if not apagado:
        return jsonify({"erro": "nao encontrado"}), 404
    return jsonify({"removido": uid}), 200


@app.route("/api/relatorio")
def relatorio():
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tabela_inexistente")  # continua quebrando de proposito
    resultado = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(resultado)


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=int(os.getenv("PORT", "5010")))
