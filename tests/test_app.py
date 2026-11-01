import re
import sqlite3
import tempfile
import unittest
from pathlib import Path

from werkzeug.security import check_password_hash

from app import app


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        app.config.update(
            TESTING=True,
            SECRET_KEY="test-secret",
            DATABASE=str(Path(self.temp_dir.name) / "test.sqlite3"),
        )
        self.client = app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def csrf_token(self, html):
        match = re.search(r'name="csrf_token" value="([^"]+)"', html)
        self.assertIsNotNone(match)
        return match.group(1)

    def create_admin(self):
        page = self.client.get("/setup")
        return self.client.post(
            "/setup",
            data={
                "csrf_token": self.csrf_token(page.get_data(as_text=True)),
                "name": "Administradora",
                "email": "admin@example.com",
                "password": "segura12",
            },
            follow_redirects=True,
        )

    def test_initial_access_requires_admin_setup(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/setup")

        page = self.client.get("/setup")
        self.assertEqual(page.status_code, 200)
        self.assertIn("Configurar acesso administrador", page.get_data(as_text=True))

    def test_admin_setup_and_dashboard_authentication(self):
        page = self.client.get("/setup")
        token = self.csrf_token(page.get_data(as_text=True))
        response = self.client.post(
            "/setup",
            data={
                "csrf_token": token,
                "name": "Administradora",
                "email": "admin@example.com",
                "password": "segura12",
            },
            follow_redirects=True,
        )
        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Administradora", html)
        self.assertIn("Acessos autorizados", html)
        self.assertIn("Criar acesso", html)
        self.assertNotIn("PORTAL DE GESTÃO", html)

        blocked_setup = self.client.get("/setup")
        self.assertEqual(blocked_setup.status_code, 302)
        self.assertEqual(blocked_setup.headers["Location"], "/")

    def test_admin_creates_users_with_hashed_password_and_duplicate_is_rejected(self):
        self.create_admin()
        page = self.client.get("/")
        token = self.csrf_token(page.get_data(as_text=True))
        response = self.client.post(
            "/users",
            data={
                "csrf_token": token,
                "name": "Pessoa Operadora",
                "email": "operadora@example.com",
                "role": "Operador",
                "password": "oper1234",
            },
            follow_redirects=True,
        )
        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Pessoa Operadora", html)
        self.assertIn("Acesso criado", html)

        db = sqlite3.connect(app.config["DATABASE"])
        try:
            row = db.execute(
                "SELECT password_hash, role FROM users WHERE email = ?",
                ("operadora@example.com",),
            ).fetchone()
        finally:
            db.close()
        self.assertTrue(check_password_hash(row[0], "oper1234"))
        self.assertEqual(row[1], "Operador")

        duplicate = self.client.post(
            "/users",
            data={
                "csrf_token": self.csrf_token(html),
                "name": "Pessoa Duplicada",
                "email": "OPERADORA@example.com",
                "role": "Operador",
                "password": "outra123",
            },
            follow_redirects=True,
        )
        self.assertIn("Já existe um acesso", duplicate.get_data(as_text=True))

    def test_non_admin_cannot_create_users(self):
        self.create_admin()
        dashboard = self.client.get("/")
        self.client.post(
            "/users",
            data={
                "csrf_token": self.csrf_token(dashboard.get_data(as_text=True)),
                "name": "Pessoa Operadora",
                "email": "operadora@example.com",
                "role": "Operador",
                "password": "oper1234",
            },
        )
        self.client.post("/logout", data={"csrf_token": self.csrf_token(dashboard.get_data(as_text=True))})

        login_page = self.client.get("/login")
        response = self.client.post(
            "/login",
            data={
                "csrf_token": self.csrf_token(login_page.get_data(as_text=True)),
                "email": "operadora@example.com",
                "password": "oper1234",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.change_password("oper1234", "oper5678")
        dashboard = self.client.get("/")
        response = self.client.post(
            "/users",
            data={
                "csrf_token": self.csrf_token(dashboard.get_data(as_text=True)),
                "name": "Tentativa indevida",
                "email": "indevida@example.com",
                "role": "Operador",
                "password": "bloq1234",
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_health_endpoint(self):
        self.assertEqual(self.client.get("/health").get_json(), {"status": "ok"})

    def post_form(self, url, page_url, data):
        page = self.client.get(page_url)
        data = dict(data, csrf_token=self.csrf_token(page.get_data(as_text=True)))
        return self.client.post(url, data=data, follow_redirects=True)

    def change_password(self, current, new, confirm=None):
        return self.post_form(
            "/conta/senha",
            "/conta/senha",
            {"current_password": current, "new_password": new, "confirm_password": new if confirm is None else confirm},
        )

    def login_as(self, email, password):
        page = self.client.get("/login")
        return self.client.post(
            "/login",
            data={"csrf_token": self.csrf_token(page.get_data(as_text=True)), "email": email, "password": password},
        )

    def logout(self):
        page = self.client.get("/conta/senha")
        self.client.post("/logout", data={"csrf_token": self.csrf_token(page.get_data(as_text=True))})

    def new_user(self, password="oper1234"):
        self.post_form(
            "/users",
            "/",
            {"name": "Pessoa Operadora", "email": "operadora@example.com", "role": "Operador", "password": password},
        )

    def test_password_length_is_6_to_8(self):
        self.create_admin()
        for bad in ("12345", "123456789"):
            html = self.post_form(
                "/users",
                "/",
                {"name": "Pessoa", "email": "p@example.com", "role": "Operador", "password": bad},
            ).get_data(as_text=True)
            self.assertIn("de 6 a 8 caracteres", html)
        self.new_user("123456")
        self.logout()
        self.assertEqual(self.login_as("operadora@example.com", "123456").status_code, 302)

    def test_new_user_must_change_password_on_first_login(self):
        self.create_admin()
        self.new_user()
        self.logout()
        self.login_as("operadora@example.com", "oper1234")
        blocked = self.client.get("/m/veiculos")
        self.assertEqual(blocked.status_code, 302)
        self.assertEqual(blocked.headers["Location"], "/conta/senha")

        self.assertIn("A senha atual está incorreta", self.change_password("errada12", "novo1234").get_data(as_text=True))
        self.assertIn("de 6 a 8 caracteres", self.change_password("oper1234", "123").get_data(as_text=True))
        self.assertIn("não confere", self.change_password("oper1234", "novo1234", "outro123").get_data(as_text=True))
        self.assertIn("diferente da atual", self.change_password("oper1234", "oper1234").get_data(as_text=True))
        self.assertIn("Senha alterada", self.change_password("oper1234", "novo1234").get_data(as_text=True))
        self.assertEqual(self.client.get("/m/veiculos").status_code, 200)

        self.logout()
        self.assertEqual(self.login_as("operadora@example.com", "oper1234").status_code, 200)
        self.assertEqual(self.login_as("operadora@example.com", "novo1234").status_code, 302)

    def test_forgot_password_and_admin_reset(self):
        self.create_admin()
        self.new_user()
        self.logout()
        page = self.client.get("/esqueci-senha")
        self.assertEqual(page.status_code, 200)
        answer = self.client.post(
            "/esqueci-senha",
            data={"csrf_token": self.csrf_token(page.get_data(as_text=True)), "email": "operadora@example.com"},
            follow_redirects=True,
        ).get_data(as_text=True)
        self.assertIn("Solicitação enviada", answer)
        unknown = self.client.post(
            "/esqueci-senha",
            data={"csrf_token": self.csrf_token(self.client.get("/esqueci-senha").get_data(as_text=True)), "email": "naoexiste@example.com"},
            follow_redirects=True,
        ).get_data(as_text=True)
        self.assertIn("Solicitação enviada", unknown)

        self.login_as("admin@example.com", "segura12")
        dashboard = self.client.get("/").get_data(as_text=True)
        self.assertIn("Pediu nova senha", dashboard)
        db = sqlite3.connect(app.config["DATABASE"])
        user_id = db.execute("SELECT id FROM users WHERE email = ?", ("operadora@example.com",)).fetchone()[0]
        db.close()
        html = self.post_form(f"/users/{user_id}/reset-password", "/", {}).get_data(as_text=True)
        match = re.search(r"Senha temporária de Pessoa Operadora: (\S{8}) ", html)
        self.assertIsNotNone(match)
        temp = match.group(1)
        self.assertNotIn("Pediu nova senha", self.client.get("/").get_data(as_text=True))

        self.logout()
        self.assertEqual(self.login_as("operadora@example.com", "oper1234").status_code, 200)
        self.login_as("operadora@example.com", temp)
        self.assertEqual(self.client.get("/").headers["Location"], "/conta/senha")
        self.assertIn("Senha alterada", self.change_password(temp, "final123"[:8]).get_data(as_text=True))

    def test_login_is_locked_after_repeated_failures(self):
        from app import LOGIN_FAILS

        LOGIN_FAILS.clear()
        self.create_admin()
        self.logout()
        for _ in range(5):
            self.login_as("admin@example.com", "errada12")
        page = self.client.get("/login")
        html = self.client.post(
            "/login",
            data={"csrf_token": self.csrf_token(page.get_data(as_text=True)), "email": "admin@example.com", "password": "segura12"},
        ).get_data(as_text=True)
        self.assertIn("Muitas tentativas", html)
        LOGIN_FAILS.clear()

    def test_admin_can_create_edit_and_delete_vehicle(self):
        self.create_admin()
        page = self.client.get("/m/veiculos")
        self.assertEqual(page.status_code, 200)
        self.assertIn("Novo veículo", page.get_data(as_text=True))

        vehicle = {"unidade": "Santos", "frota": "12", "placa": "abc-1d23", "modelo": "Van", "marca": "Fiat", "ano": "2022", "km": "100", "status": "Disponível"}
        html = self.post_form("/m/veiculos", "/m/veiculos", vehicle).get_data(as_text=True)
        self.assertIn("ABC-1D23", html)
        self.assertIn("salvo", html)

        duplicate = self.post_form("/m/veiculos", "/m/veiculos", vehicle).get_data(as_text=True)
        self.assertIn("Já existe um veículo", duplicate)

        db = sqlite3.connect(app.config["DATABASE"])
        record_id = db.execute("SELECT id FROM records").fetchone()[0]
        db.close()
        vehicle["status"] = "Em manutenção"
        html = self.post_form(f"/m/veiculos/{record_id}", "/m/veiculos", vehicle).get_data(as_text=True)
        self.assertIn("atualizados", html)
        self.assertIn("Em manutenção", html)

        html = self.post_form(f"/m/veiculos/{record_id}/delete", "/m/veiculos", {}).get_data(as_text=True)
        self.assertIn("excluído", html)
        self.assertNotIn("ABC-1D23", html)

    def test_other_modules_require_registered_vehicle_and_valid_data(self):
        self.create_admin()
        movement = {"data": "2026-10-14T07:30", "placa": "XXX-0000", "motorista": "Ana", "origem": "A", "destino": "B", "km": "10"}
        html = self.post_form("/m/movimentacoes", "/m/movimentacoes", movement).get_data(as_text=True)
        self.assertIn("Selecione um veículo cadastrado", html)

        self.post_form(
            "/m/veiculos",
            "/m/veiculos",
            {"unidade": "Santos", "frota": "12", "placa": "ABC-1D23", "modelo": "Van", "marca": "Fiat", "ano": "2022", "status": "Disponível"},
        )
        movement.update(
            placa="ABC-1D23", solicitante="Dra. Paula", recebedor="Carlos", previsao_recebimento="2026-10-30"
        )
        html = self.post_form("/m/movimentacoes", "/m/movimentacoes", movement).get_data(as_text=True)
        self.assertIn("Dra. Paula", html)
        self.assertIn("Frota 12", html)
        self.assertIn("30/10/2026", html)
        missing = dict(movement, recebedor="")
        html = self.post_form("/m/movimentacoes", "/m/movimentacoes", missing).get_data(as_text=True)
        self.assertIn("Preencha o campo Quem recebe o veículo", html)
        invalid = self.post_form("/m/veiculos", "/m/veiculos", {"placa": "", "modelo": "x"}).get_data(as_text=True)
        self.assertIn("Preencha o campo Unidade", invalid)

    def test_read_only_user_cannot_edit(self):
        self.create_admin()
        self.post_form(
            "/users",
            "/",
            {"name": "Leitor", "email": "leitor@example.com", "role": "Somente leitura", "password": "leitor12"},
        )
        page = self.client.get("/")
        self.client.post("/logout", data={"csrf_token": self.csrf_token(page.get_data(as_text=True))})
        login = self.client.get("/login")
        self.client.post(
            "/login",
            data={"csrf_token": self.csrf_token(login.get_data(as_text=True)), "email": "leitor@example.com", "password": "leitor12"},
        )
        self.change_password("leitor12", "leitor34")
        listing = self.client.get("/m/veiculos")
        self.assertEqual(listing.status_code, 200)
        self.assertNotIn("Novo veículo", listing.get_data(as_text=True))
        response = self.client.post(
            "/m/veiculos",
            data={"csrf_token": self.csrf_token(listing.get_data(as_text=True)), "placa": "ZZZ-1111"},
        )
        self.assertEqual(response.status_code, 403)

    def test_dashboard_reflects_registered_data(self):
        self.create_admin()
        html = self.client.get("/").get_data(as_text=True)
        self.assertNotIn("+2 este mês", html)
        self.assertIn("Nenhuma movimentação registrada", html)
        self.assertIn("Nenhum prazo cadastrado", html)

        vehicle = {"unidade": "Santos", "frota": "12", "placa": "ABC-1D23", "modelo": "Van", "marca": "Fiat", "ano": "2022", "km": "0", "status": "Em operação"}
        self.post_form("/m/veiculos", "/m/veiculos", vehicle)
        self.post_form(
            "/m/manutencoes",
            "/m/manutencoes",
            {"placa": "ABC-1D23", "tipo": "Preventiva", "descricao": "Revisão", "km_atual": "9800", "km_revisao": "10000", "previsao": "2000-01-01", "status": "Agendada"},
        )
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn("faltam 200 km para a revisão", html)
        self.post_form(
            "/m/manutencoes",
            "/m/manutencoes",
            {"placa": "ABC-1D23", "tipo": "Preventiva", "descricao": "Outra", "km_atual": "10600", "km_revisao": "10000", "previsao": "2099-01-01", "status": "Agendada"},
        )
        listing = self.client.get("/m/manutencoes").get_data(as_text=True)
        self.assertIn("revisão ultrapassada em 600 km", listing)
        far = self.post_form(
            "/m/manutencoes",
            "/m/manutencoes",
            {"placa": "ABC-1D23", "tipo": "Preventiva", "descricao": "Longe", "km_atual": "1000", "km_revisao": "10000", "previsao": "2099-01-01", "status": "Agendada"},
        ).get_data(as_text=True)
        self.assertNotIn("faltam 9.000 km", far)
        missing = self.post_form(
            "/m/manutencoes",
            "/m/manutencoes",
            {"placa": "ABC-1D23", "tipo": "Preventiva", "descricao": "Sem km", "previsao": "2099-01-01", "status": "Agendada"},
        ).get_data(as_text=True)
        self.assertIn("informe o km atual e o km da revisão", missing)
        html = self.client.get("/").get_data(as_text=True)
        self.assertRegex(html, r'stat-value">1 <span class="stat-percent">100%')
        self.assertIn("venceu há", html)
        self.assertNotIn("48", html)

    def test_seguro_alert_40_days(self):
        self.create_admin()
        self.post_form(
            "/m/veiculos",
            "/m/veiculos",
            {"unidade": "Santos", "frota": "12", "placa": "ABC-1D23", "modelo": "Van", "marca": "Fiat", "ano": "2022", "status": "Disponível"},
        )
        from datetime import date, timedelta

        def policy(days, status="Vigente"):
            return {
                "placa": "ABC-1D23", "seguradora": "X", "apolice": str(days),
                "vigencia": (date.today() + timedelta(days=days)).isoformat(), "status": status,
            }

        self.post_form("/m/seguros", "/m/seguros", policy(40))
        self.post_form("/m/seguros", "/m/seguros", policy(41))
        self.post_form("/m/seguros", "/m/seguros", policy(-3))
        self.post_form("/m/seguros", "/m/seguros", policy(-10, "Renovada"))
        listing = self.client.get("/m/seguros").get_data(as_text=True)
        self.assertIn("vence em 40 dia(s)", listing)
        self.assertNotIn("vence em 41 dia(s)", listing)
        self.assertIn("vencido há 3 dia(s)", listing)
        self.assertNotIn("vencido há 10 dia(s)", listing)
        dashboard = self.client.get("/").get_data(as_text=True)
        self.assertIn("Renovações de seguro", dashboard)
        self.assertIn("vence em 40 dia(s)", dashboard)

    def test_sale_marks_vehicle_as_sold_and_delete_restores(self):
        self.create_admin()
        vehicle = {"unidade": "Santos", "frota": "12", "placa": "ABC-1D23", "modelo": "Van", "marca": "Fiat", "ano": "2022", "status": "Disponível"}
        self.post_form("/m/veiculos", "/m/veiculos", vehicle)
        sale = {
            "placa": "ABC-1D23", "comprador": "João", "contato": "11 99999-0000", "endereco": "Rua A, 1",
            "data_venda": "2026-10-20", "valor": "35000", "vendedor": "Maria",
        }
        html = self.post_form("/m/vendas", "/m/vendas", sale).get_data(as_text=True)
        self.assertIn("João", html)
        self.assertIn("<td>Vendido</td>", self.client.get("/m/veiculos").get_data(as_text=True))
        again = self.post_form("/m/vendas", "/m/vendas", sale).get_data(as_text=True)
        self.assertIn("já tem uma venda", again)
        db = sqlite3.connect(app.config["DATABASE"])
        sale_id = db.execute("SELECT id FROM records WHERE module = 'vendas'").fetchone()[0]
        db.close()
        self.post_form(f"/m/vendas/{sale_id}/delete", "/m/vendas", {})
        self.assertIn("<td>Disponível</td>", self.client.get("/m/veiculos").get_data(as_text=True))

    def test_unknown_module_returns_404(self):
        self.create_admin()
        self.assertEqual(self.client.get("/m/inexistente").status_code, 404)


if __name__ == "__main__":
    unittest.main()
