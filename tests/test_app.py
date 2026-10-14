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

    def test_home_serves_portuguese_dashboard(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        self.assertIn('lang="pt-BR"', page)
        self.assertIn("Acessos autorizados", page)
        self.assertIn("Visão geral", page)
        self.assertIn("Perfis demonstrativos", page)
        self.assertIn('id="user-search"', page)
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
