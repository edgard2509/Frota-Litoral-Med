# Frota-Litoral-Med
Sistema de gestão de frota da Litoral Med — controle de movimentações e manutenções.

## Como executar localmente

Requer Python 3.10 ou superior.

```bash
python -m pip install -r requirements.txt
python app.py
```

A aplicação fica disponível em `http://localhost:8000`.

## Publicar no Render

### Configuração do serviço
- **Environment**: Python
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn app:app`

### Variáveis de ambiente
- Nenhuma obrigatória

### Observações
- A rota `/health` retorna `{"status":"ok"}`.
- O app usa a variável `PORT` em produção quando disponível.

## Testes

```bash
python -m unittest tests.test_app
```
