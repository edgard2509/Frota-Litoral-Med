from flask import Flask, jsonify, render_template

import data

app = Flask(__name__)


@app.template_filter("brl")
def brl(value):
    return "R$ " + f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


@app.template_filter("num")
def num(value):
    return f"{value:,}".replace(",", ".")


@app.route("/")
def home():
    return render_template(
        "index.html",
        kpis=data.kpis(),
        veiculos=data.VEICULOS,
        movimentacoes=data.MOVIMENTACOES,
        manutencoes=data.MANUTENCOES,
    )


@app.route("/health")
def health():
    return jsonify(status="ok")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
