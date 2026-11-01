# Frota Litoral Med

Portal em português para acompanhamento da frota, movimentações, manutenções e acessos autorizados. Os dados exibidos são demonstrativos.

## Executar localmente ou no GitHub Codespaces

Requer Python 3.10 ou superior.

```bash
python -m pip install -r requirements.txt
python app.py
```

A aplicação fica disponível em `http://localhost:8000`. Se a variável `PORT` estiver definida, ela será usada no lugar da porta local padrão. O endpoint `GET /health` retorna `{"status":"ok"}`.

## Publicar no Render

Crie um **Web Service** no Render conectado a este repositório. O `render.yaml` configura automaticamente o comando de build e o comando de inicialização com Gunicorn. Se configurar o serviço manualmente, use:

- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn app:app --bind 0.0.0.0:$PORT`

## Testes

```bash
python -m unittest discover -s tests
```
