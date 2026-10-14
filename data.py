"""Dados de demonstração do portal da frota."""
from collections import Counter

VEICULOS = [
    {"placa": "LMD-2A01", "modelo": "Ambulância UTI Móvel", "marca": "Mercedes Sprinter", "ano": 2021, "km": 84210, "status": "Em operação"},
    {"placa": "LMD-3B12", "modelo": "Ambulância Simples", "marca": "Fiat Ducato", "ano": 2019, "km": 126540, "status": "Disponível"},
    {"placa": "LMD-4C23", "modelo": "Van Transporte de Pacientes", "marca": "Renault Master", "ano": 2022, "km": 45890, "status": "Em operação"},
    {"placa": "LMD-5D34", "modelo": "Utilitário Administrativo", "marca": "Fiat Fiorino", "ano": 2020, "km": 71300, "status": "Em manutenção"},
    {"placa": "LMD-6E45", "modelo": "Ambulância UTI Móvel", "marca": "Peugeot Boxer", "ano": 2023, "km": 22150, "status": "Disponível"},
    {"placa": "LMD-7F56", "modelo": "Carro de Apoio", "marca": "Toyota Corolla", "ano": 2022, "km": 38700, "status": "Em operação"},
]

MOVIMENTACOES = [
    {"data": "14/10/2026 07:30", "placa": "LMD-2A01", "motorista": "Carlos Almeida", "origem": "Base Litoral", "destino": "Hospital Regional", "km": 42},
    {"data": "14/10/2026 08:15", "placa": "LMD-4C23", "motorista": "Marina Souza", "origem": "Clínica Central", "destino": "Residência do paciente", "km": 18},
    {"data": "13/10/2026 16:40", "placa": "LMD-7F56", "motorista": "João Pereira", "origem": "Base Litoral", "destino": "Unidade Praia Norte", "km": 27},
    {"data": "13/10/2026 11:05", "placa": "LMD-3B12", "motorista": "Rita Lima", "origem": "Hospital Regional", "destino": "Base Litoral", "km": 39},
]

MANUTENCOES = [
    {"placa": "LMD-5D34", "tipo": "Corretiva", "descricao": "Troca de embreagem", "previsao": "16/10/2026", "custo": 2850.00, "status": "Em andamento"},
    {"placa": "LMD-3B12", "tipo": "Preventiva", "descricao": "Revisão 130.000 km", "previsao": "22/10/2026", "custo": 1400.00, "status": "Agendada"},
    {"placa": "LMD-2A01", "tipo": "Preventiva", "descricao": "Troca de óleo e filtros", "previsao": "30/10/2026", "custo": 980.00, "status": "Agendada"},
    {"placa": "LMD-6E45", "tipo": "Preventiva", "descricao": "Inspeção de equipamentos de UTI", "previsao": "05/10/2026", "custo": 650.00, "status": "Concluída"},
]


def kpis():
    status = Counter(v["status"] for v in VEICULOS)
    total = len(VEICULOS)
    abertas = [m for m in MANUTENCOES if m["status"] != "Concluída"]
    return {
        "total": total,
        "em_operacao": status["Em operação"],
        "disponiveis": status["Disponível"],
        "em_manutencao": status["Em manutenção"],
        "disponibilidade": round(100 * (total - status["Em manutenção"]) / total) if total else 0,
        "km_mes": sum(m["km"] for m in MOVIMENTACOES),
        "manutencoes_abertas": len(abertas),
        "custo_manutencao": sum(m["custo"] for m in MANUTENCOES),
    }
