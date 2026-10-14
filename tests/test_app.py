from app import app


def test_home():
    r = app.test_client().get("/")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    for s in ("Veículos", "Movimentações", "Manutenções", "Indicadores", "20"):
        assert s in body


def test_health():
    assert app.test_client().get("/health").get_json() == {"status": "ok"}
