"""Definição dos módulos de cadastro da frota (campos, rótulos e validações)."""
from datetime import datetime

STATUS_VEICULO = ("Em operação", "Disponível", "Em manutenção", "Inativo", "Disponível para Venda", "Vendido")

MODULES = {
    "veiculos": {
        "title": "Veículos",
        "singular": "veículo",
        "description": "Cadastre e acompanhe os veículos da frota e sua disponibilidade.",
        "fields": [
            {"name": "unidade", "label": "Unidade", "type": "text", "required": True},
            {"name": "frota", "label": "Frota", "type": "text", "required": True},
            {"name": "placa", "label": "Placa", "type": "text", "required": True, "upper": True},
            {"name": "modelo", "label": "Modelo", "type": "text", "required": True},
            {"name": "marca", "label": "Marca", "type": "text", "required": True},
            {"name": "ano", "label": "Ano", "type": "int", "required": True, "min": 1980, "max": 2100},
            {"name": "km", "label": "Km rodados", "type": "int", "required": False, "min": 0},
            {"name": "status", "label": "Status", "type": "select", "required": True, "options": STATUS_VEICULO},
        ],
    },
    "movimentacoes": {
        "title": "Movimentações",
        "singular": "movimentação",
        "description": "Registre as saídas, deslocamentos e solicitações da frota.",
        "fields": [
            {"name": "data", "label": "Data e hora", "type": "datetime", "required": True},
            {"name": "placa", "label": "Veículo", "type": "placa", "required": True},
            {"name": "motorista", "label": "Motorista", "type": "text", "required": True},
            {"name": "origem", "label": "Origem", "type": "text", "required": True},
            {"name": "destino", "label": "Destino", "type": "text", "required": True},
            {"name": "solicitante", "label": "Quem solicita", "type": "text", "required": True},
            {"name": "recebedor", "label": "Quem recebe o veículo", "type": "text", "required": True},
            {"name": "previsao_recebimento", "label": "Data prevista de recebimento", "type": "date", "required": True},
            {"name": "km", "label": "Km percorridos", "type": "int", "required": False, "min": 0},
        ],
    },
    "manutencoes": {
        "title": "Manutenções",
        "singular": "manutenção",
        "description": "Acompanhe os serviços e planos de manutenção.",
        "fields": [
            {"name": "placa", "label": "Veículo", "type": "placa", "required": True},
            {"name": "tipo", "label": "Tipo", "type": "select", "required": True, "options": ("Preventiva", "Corretiva")},
            {"name": "descricao", "label": "Descrição", "type": "text", "required": True},
            {"name": "km_atual", "label": "Km atual", "type": "int", "required": False, "min": 0},
            {"name": "km_revisao", "label": "Km da revisão", "type": "int", "required": False, "min": 0},
            {"name": "previsao", "label": "Previsão", "type": "date", "required": True},
            {"name": "custo", "label": "Custo (R$)", "type": "money", "required": False, "min": 0},
            {"name": "status", "label": "Status", "type": "select", "required": True, "options": ("Agendada", "Em andamento", "Concluída", "Cancelada")},
        ],
    },
    "licenciamentos": {
        "title": "Licenciamentos",
        "singular": "licenciamento",
        "description": "Controle documentos e prazos de licenciamento.",
        "fields": [
            {"name": "placa", "label": "Veículo", "type": "placa", "required": True},
            {"name": "exercicio", "label": "Exercício", "type": "int", "required": True, "min": 2000, "max": 2100},
            {"name": "vencimento", "label": "Vencimento", "type": "date", "required": True},
            {"name": "valor", "label": "Valor (R$)", "type": "money", "required": False, "min": 0},
            {"name": "status", "label": "Status", "type": "select", "required": True, "options": ("Em dia", "A vencer", "Vencido")},
        ],
    },
    "seguros": {
        "title": "Seguros",
        "singular": "seguro",
        "description": "Controle as apólices e vigências dos veículos.",
        "fields": [
            {"name": "placa", "label": "Veículo", "type": "placa", "required": True},
            {"name": "seguradora", "label": "Seguradora", "type": "text", "required": True},
            {"name": "apolice", "label": "Apólice", "type": "text", "required": True},
            {"name": "vigencia", "label": "Fim da vigência", "type": "date", "required": True},
            {"name": "valor", "label": "Valor (R$)", "type": "money", "required": False, "min": 0},
            {"name": "status", "label": "Status", "type": "select", "required": True, "options": ("Vigente", "A vencer", "Vencida", "Renovada", "Cancelada")},
        ],
    },
    "sinistros": {
        "title": "Sinistros",
        "singular": "sinistro",
        "description": "Acompanhe as ocorrências registradas na frota.",
        "fields": [
            {"name": "data", "label": "Data", "type": "date", "required": True},
            {"name": "placa", "label": "Veículo", "type": "placa", "required": True},
            {"name": "tipo", "label": "Tipo", "type": "select", "required": True, "options": ("Colisão", "Roubo/Furto", "Avaria", "Outro")},
            {"name": "descricao", "label": "Descrição", "type": "text", "required": True},
            {"name": "valor", "label": "Valor estimado (R$)", "type": "money", "required": False, "min": 0},
            {"name": "status", "label": "Status", "type": "select", "required": True, "options": ("Aberto", "Em análise", "Encerrado")},
        ],
    },
    "vendas": {
        "title": "Veículos Vendidos",
        "singular": "venda",
        "description": "Controle os veículos vendidos, com dados do comprador e da negociação.",
        "fields": [
            {"name": "placa", "label": "Veículo", "type": "placa", "required": True},
            {"name": "comprador", "label": "Nome do comprador", "type": "text", "required": True},
            {"name": "contato", "label": "Contato", "type": "text", "required": True},
            {"name": "endereco", "label": "Endereço", "type": "text", "required": True},
            {"name": "data_venda", "label": "Data da venda", "type": "date", "required": True},
            {"name": "valor", "label": "Valor da venda (R$)", "type": "money", "required": True, "min": 0},
            {"name": "vendedor", "label": "Nome do vendedor", "type": "text", "required": True},
        ],
    },
}

TEXT_LIMIT = 200


def clean_record(module, form, plates):
    """Valida o formulário e devolve (dados, erro)."""
    data = {}
    for field in module["fields"]:
        raw = (form.get(field["name"]) or "").strip()
        label, kind = field["label"], field["type"]
        if not raw:
            if field["required"]:
                return None, f"Preencha o campo {label}."
            data[field["name"]] = None
            continue
        if len(raw) > TEXT_LIMIT:
            return None, f"O campo {label} é muito longo."
        try:
            if kind in ("text", "select", "placa"):
                value = raw.upper() if field.get("upper") else raw
                if kind == "select" and value not in field["options"]:
                    return None, f"Valor inválido para {label}."
                if kind == "placa" and value not in plates:
                    return None, "Selecione um veículo cadastrado."
            elif kind == "int":
                value = int(raw)
            elif kind == "money":
                value = round(float(raw.replace(",", ".")), 2)
            elif kind == "date":
                value = datetime.strptime(raw, "%Y-%m-%d").strftime("%Y-%m-%d")
            elif kind == "datetime":
                value = datetime.strptime(raw, "%Y-%m-%dT%H:%M").strftime("%Y-%m-%dT%H:%M")
            else:
                return None, f"Campo inválido: {label}."
        except ValueError:
            return None, f"Valor inválido para {label}."
        if kind in ("int", "money"):
            if "min" in field and value < field["min"]:
                return None, f"{label} não pode ser menor que {field['min']}."
            if "max" in field and value > field["max"]:
                return None, f"{label} não pode ser maior que {field['max']}."
        data[field["name"]] = value
    return data, None
