# Frota-Litoral-Med
Sistema de gestão de frota da Litoral Med — controle de movimentações e manutenções.

## Executando (Codespaces)
## Executando (Codespaces / local)

```bash
pip install -r requirements.txt
python app.py
```

O site escuta em `0.0.0.0:8000` (porta encaminhada automaticamente no Codespaces). Rota de verificação: `/health`.
O dev container já instala as dependências e inicia o app.
O portal escuta em `0.0.0.0:8000`. Rotas: `/` (portal) e `/health`.
Os dados são de demonstração (`data.py`).
## Executando

```bash
pip install -r requirements.txt
python app.py   # http://localhost:8000
```

Endpoint de saúde: `/health`.
# Frota Litoral Med

Portal interno em português para acompanhamento da frota, movimentações, manutenção e acessos autorizados.

## Executar localmente ou no GitHub Codespaces

Requer Python 3.10 ou superior.

```bash
python -m pip install -r requirements.txt
python app.py
```

A aplicação fica disponível em `http://localhost:8000` e escuta em `0.0.0.0:8000`, permitindo o encaminhamento da porta 8000 no Codespaces.

O endpoint `GET /health` retorna `{"status":"ok"}` para verificações de disponibilidade.

Para executar os testes:

```bash
python -m unittest tests.test_app
```

Os indicadores e perfis de usuário exibidos na interface são demonstrativos; conecte dados reais antes de utilizar o portal em produção.
