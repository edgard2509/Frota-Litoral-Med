import os

from flask import Flask, jsonify, render_template

import data

app = Flask(__name__)

MENU = [
    ("visao-geral", "Visão geral"),
    ("veiculos", "Veículos"),
    ("movimentacoes", "Movimentações"),
    ("manutencoes", "Manutenções"),
    ("licenciamentos", "Licenciamentos"),
    ("seguros", "Seguros"),
    ("sinistros", "Sinistros"),
    ("usuarios", "Usuários"),
]

USUARIOS = [
    {"nome": "Administrador", "email": "admin@litoralmed.com.br", "perfil": "Administrador", "status": "Ativo"},
    {"nome": "Gestor de Frota", "email": "frota@litoralmed.com.br", "perfil": "Gestor", "status": "Ativo"},
    {"nome": "Operações", "email": "operacoes@litoralmed.com.br", "perfil": "Operador", "status": "Ativo"},
    {"nome": "Manutenção", "email": "manutencao@litoralmed.com.br", "perfil": "Operador", "status": "Inativo"},
]


@app.template_filter("brl")
def brl(value):
    return "R$ " + f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


@app.template_filter("num")
def num(value):
    return f"{value:,}".replace(",", ".")


@app.get("/")
def home():
    return render_template(
        "index.html",
        kpis=data.kpis(),
        veiculos=data.VEICULOS,
        movimentacoes=data.MOVIMENTACOES,
        manutencoes=data.MANUTENCOES,
        menu=MENU,
        ativo="usuarios",
        usuarios=USUARIOS,
    )


@app.get("/health")
def health():
    return jsonify(status="ok")


def run():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")), debug=False)


if __name__ == "__main__":
    run()
