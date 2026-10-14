from app import app


def test_health():
    assert app.test_client().get("/health").get_json() == {"status": "ok"}


def test_index_has_menu_and_users():
    html = app.test_client().get("/").get_data(as_text=True)
    for item in ("Visão geral", "Veículos", "Movimentações", "Manutenções",
                 "Licenciamentos", "Seguros", "Sinistros", "Usuários", "20"):
        assert item in html
