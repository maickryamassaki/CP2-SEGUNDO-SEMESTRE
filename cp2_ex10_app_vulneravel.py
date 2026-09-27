# laboratorio apenas - copia local do app_vulneravel.py do enunciado.
# nao mudei a logica, so troquei a senha fixa pra bater com o meu mysql
# local. continua sendo senha hardcoded no codigo, que e' exatamente
# uma das falhas que o exploit.py vai provar
from flask import Flask, request, jsonify
import mysql.connector

app = Flask(__name__)
SENHA_MESTRA = "Cyber@2024"


def db():
    return mysql.connector.connect(host="localhost", user="root",
                                    password="root", database="seguranca")


@app.route("/api/usuarios/buscar")
def buscar():
    nome = request.args.get("nome", "")
    conn = db()  # precisa ficar numa variavel, senao o mysql-connector
    cur = conn.cursor(dictionary=True)  # derruba a conexao antes do execute
    cur.execute(f"SELECT * FROM usuarios WHERE nome LIKE '%{nome}%'")
    return jsonify(cur.fetchall())


@app.route("/perfil")
def perfil():
    return f"<h1>Bem-vindo, {request.args.get('u','')}</h1>"


@app.route("/api/usuarios/<int:uid>", methods=["DELETE"])
def remover(uid):
    con = db()
    cur = con.cursor()
    cur.execute("DELETE FROM usuarios WHERE id = %s", (uid,))
    con.commit()
    return jsonify({"removido": uid})


@app.route("/api/relatorio")
def relatorio():
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tabela_inexistente")
    return jsonify(cur.fetchall())


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")