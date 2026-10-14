from flask import Flask, render_template

app = Flask(__name__)

MENU = [
    ("Visão geral", "visao-geral"),
    ("Veículos", "veiculos"),
    ("Movimentações", "movimentacoes"),
    ("Manutenções", "manutencoes"),
    ("Licenciamentos", "licenciamentos"),
    ("Seguros", "seguros"),
    ("Sinistros", "sinistros"),
    ("Usuários", "usuarios"),
]

USUARIOS = [
    {"nome": "Administrador", "email": "admin@litoralmed.com.br", "perfil": "Administrador", "ativo": True},
    {"nome": "Gestor de Frota", "email": "frota@litoralmed.com.br", "perfil": "Gestor", "ativo": True},
    {"nome": "Operação", "email": "operacao@litoralmed.com.br", "perfil": "Operador", "ativo": True},
    {"nome": "Financeiro", "email": "financeiro@litoralmed.com.br", "perfil": "Consulta", "ativo": False},
]


@app.route("/")
def index():
    return render_template("index.html", menu=MENU, usuarios=USUARIOS, ativo="usuarios")


@app.route("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
