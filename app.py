from flask import Flask, render_template

app = Flask(__name__)

VEICULOS = [
    {"placa": "LMD-2A01", "modelo": "Fiat Ducato Ambulância", "tipo": "Ambulância", "status": "Em operação", "km": 84210},
    {"placa": "LMD-3B14", "modelo": "Renault Master UTI Móvel", "tipo": "UTI Móvel", "status": "Em operação", "km": 61530},
    {"placa": "LMD-4C27", "modelo": "VW Saveiro Apoio", "tipo": "Apoio", "status": "Em manutenção", "km": 120980},
    {"placa": "LMD-5D39", "modelo": "Mercedes Sprinter Transporte", "tipo": "Transporte", "status": "Disponível", "km": 47320},
]

MOVIMENTACOES = [
    {"data": "14/10/2026", "placa": "LMD-2A01", "motorista": "Carlos Silva", "destino": "Hospital Regional", "km": 42},
    {"data": "14/10/2026", "placa": "LMD-3B14", "motorista": "Ana Souza", "destino": "Remoção inter-hospitalar", "km": 118},
    {"data": "13/10/2026", "placa": "LMD-5D39", "motorista": "João Pereira", "destino": "Clínica Litoral", "km": 27},
]

MANUTENCOES = [
    {"placa": "LMD-4C27", "servico": "Troca de embreagem", "previsao": "16/10/2026", "status": "Em andamento"},
    {"placa": "LMD-2A01", "servico": "Revisão 90.000 km", "previsao": "25/10/2026", "status": "Agendada"},
    {"placa": "LMD-3B14", "servico": "Troca de pneus", "previsao": "02/11/2026", "status": "Agendada"},
]


def indicadores():
    total = len(VEICULOS)
    em_operacao = sum(v["status"] == "Em operação" for v in VEICULOS)
    em_manutencao = sum(v["status"] == "Em manutenção" for v in VEICULOS)
    return {
        "total": total,
        "em_operacao": em_operacao,
        "em_manutencao": em_manutencao,
        "movimentacoes": len(MOVIMENTACOES),
        "km_total": sum(m["km"] for m in MOVIMENTACOES),
        "disponibilidade": round(100 * (total - em_manutencao) / total) if total else 0,
    }


@app.route("/")
def home():
    return render_template(
        "index.html",
        veiculos=VEICULOS,
        movimentacoes=MOVIMENTACOES,
        manutencoes=MANUTENCOES,
        kpi=indicadores(),
    )


@app.route("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
