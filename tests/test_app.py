import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app import app


def test_home_has_sections():
    html = app.test_client().get("/").get_data(as_text=True)
    for s in ("Veículos", "Movimentações", "Manutenções", "Indicadores", "20"):
        assert s in html


def test_health():
    assert app.test_client().get("/health").get_json() == {"status": "ok"}
