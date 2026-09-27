"""
exercicio 7 - xss onde ninguem procura: dentro do atributo

renderiza incidentes vindos do mongodb numa tabela, incluindo o nome
do ativo dentro de um atributo html (alt=""). jinja2 escapa por padrao,
entao a mesma carga que quebra um <script> tambem quebra um atributo
"""

import os

from flask import Flask, render_template_string
from markupsafe import Markup
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")

app = Flask(__name__)


def preparar_dados():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    db = client[os.getenv("MONGO_DATABASE", "cp2_bd")]
    col = db["incidentes_dashboard"]
    col.delete_many({})
    col.insert_many([
        {"titulo": "acesso suspeito", "ativo": "<script>alert('xss1')</script>"},
        {"titulo": "porta aberta", "ativo": "x\" onerror=\"alert('xss2')"},
    ])
    client.close()


def buscar_incidentes():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    db = client[os.getenv("MONGO_DATABASE", "cp2_bd")]
    incidentes = list(db["incidentes_dashboard"].find({}, {"_id": 0}))
    client.close()
    return incidentes


# template com escape automatico (padrao do jinja2). o alt="{{ ativo }}"
# vira texto escapado dentro do atributo, entao aspas dentro do valor nao
# fecham o atributo antes da hora
TEMPLATE_SEGURO = """
<!doctype html>
<table>
{% for i in incidentes %}
  <tr>
    <td>{{ i.titulo }}</td>
    <td><img src="/icone.png" alt="{{ i.ativo }}"></td>
  </tr>
{% endfor %}
</table>
"""

# versao insegura, so pra comparar: usa markup/safe pra jogar o valor cru
# no html, sem escape nenhum. um safe mal colocado aqui reabre o buraco
# porque devolve pro navegador exatamente o que o usuario mandou
TEMPLATE_INSEGURO = """
<!doctype html>
<table>
{% for i in incidentes %}
  <tr>
    <td>{{ i.titulo_cru | safe }}</td>
    <td><img src="/icone.png" alt="{{ i.ativo_cru | safe }}"></td>
  </tr>
{% endfor %}
</table>
"""


@app.after_request
def aplicar_csp(response):
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response


@app.route("/dashboard")
def dashboard():
    return render_template_string(TEMPLATE_SEGURO, incidentes=buscar_incidentes())


@app.route("/dashboard-inseguro")
def dashboard_inseguro():
    # rota so pra comparacao lado a lado, (nao usar isso em nada real)
    incidentes = buscar_incidentes()
    for i in incidentes:
        i["titulo_cru"] = Markup(i["titulo"])
        i["ativo_cru"] = Markup(i["ativo"])
    return render_template_string(TEMPLATE_INSEGURO, incidentes=incidentes)


if __name__ == "__main__":
    preparar_dados()
    app.run(debug=True, host="0.0.0.0", port=5003)
