import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app import app, run


def test_home_has_sections():
    html = app.test_client().get("/").get_data(as_text=True)
    for s in ("Veículos", "Movimentações", "Manutenções", "Indicadores", "20"):
        assert s in html


def test_health():
    assert app.test_client().get("/health").get_json() == {"status": "ok"}
from app import app


def test_health():
    assert app.test_client().get("/health").get_json() == {"status": "ok"}


def test_index_has_menu_and_users():
    html = app.test_client().get("/").get_data(as_text=True)
    for item in ("Visão geral", "Veículos", "Movimentações", "Manutenções",
                 "Licenciamentos", "Seguros", "Sinistros", "Usuários", "20"):
        assert item in html
import unittest

from app import app


class DashboardTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})

    def test_only_one_home_and_health_route(self):
        routes = [rule.rule for rule in app.url_map.iter_rules()]
        self.assertEqual(routes.count("/"), 1)
        self.assertEqual(routes.count("/health"), 1)

    def test_run_uses_platform_port_or_local_default(self):
        with patch.object(app, "run") as app_run, patch.dict(os.environ, {"PORT": "4321"}):
            run()
        app_run.assert_called_once_with(host="0.0.0.0", port=4321, debug=False)

        with patch.object(app, "run") as app_run, patch.dict(os.environ, {}, clear=True):
            run()
        app_run.assert_called_once_with(host="0.0.0.0", port=8000, debug=False)

    def test_home_serves_portuguese_dashboard(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        self.assertIn('lang="pt-BR"', page)
        self.assertIn('class="brand-name">Litoral <span>Med</span>', page)
        self.assertIn('<strong>20</strong> anos', page)
        self.assertIn("Acessos autorizados", page)
        self.assertIn("Visão geral", page)
        self.assertIn("Perfis demonstrativos", page)
        self.assertIn('id="user-search"', page)
        self.assertIn('id="user-count">5 usuários', page)
        self.assertIn('id="visible-user-count">5</strong>', page)
        self.assertNotIn("12 usuários", page)
        self.assertIn("anos", page)
        self.assertIn('class="sidebar"', page)

    def test_dashboard_assets_are_served_locally(self):
        for asset in ("styles.css", "app.js"):
            with self.subTest(asset=asset):
                response = self.client.get(f"/static/{asset}")
                try:
                    self.assertEqual(response.status_code, 200)
                    self.assertTrue(response.get_data())
                finally:
                    response.close()


if __name__ == "__main__":
    unittest.main()
