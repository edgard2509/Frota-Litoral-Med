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

Os indicadores e perfis de usuário exibidos na interface são demonstrativos; conecte dados reais antes de utilizar o portal em produção.
