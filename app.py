from flask import Flask, render_template

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


@app.route("/")
def index():
    return render_template("index.html", menu=MENU, ativo="usuarios", usuarios=USUARIOS)


@app.route("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
