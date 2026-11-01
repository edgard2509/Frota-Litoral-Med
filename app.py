import hmac
import json
import os
import secrets
import sqlite3
import time
from collections import Counter
from datetime import date
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    abort,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

import data
from modules import MODULES, clean_record

KM_WARNING = 500
SEGURO_WARNING_DAYS = 40
MONTHS = ("JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ")
MONTH_NAMES = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro")
WEEKDAYS = ("Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo")

app = Flask(__name__, instance_relative_config=True)
DATA_DIR = Path(os.environ.get("DATA_DIR") or app.instance_path)
DATA_DIR.mkdir(parents=True, exist_ok=True)
IS_PRODUCTION = os.environ.get("FLASK_ENV") == "production"
if IS_PRODUCTION:
    from werkzeug.middleware.proxy_fix import ProxyFix

    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

secret_path = DATA_DIR / "secret_key"
if not os.environ.get("SECRET_KEY") and not secret_path.exists():
    secret_path.write_text(secrets.token_hex(32), encoding="utf-8")
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY") or secret_path.read_text(encoding="utf-8").strip(),
    DATABASE=str(DATA_DIR / "portal.sqlite3"),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=IS_PRODUCTION,
)

ROLES = ("Gestor de frota", "Operador", "Somente leitura")
PASSWORD_MIN, PASSWORD_MAX = 6, 8
PASSWORD_CHANGE_ENDPOINTS = {"change_password", "logout", "static", "health"}
LOGIN_MAX_FAILS = 5
LOGIN_LOCK_SECONDS = 15 * 60
LOGIN_FAILS = {}
TEMP_PASSWORD_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"


def get_db():
    if "db" in g:
        return g.db
    db = sqlite3.connect(app.config["DATABASE"])
    db.row_factory = sqlite3.Row
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            is_admin INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_seen TEXT
        )
        """
    )
    db.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS one_admin_account ON users (is_admin) WHERE is_admin = 1"
    )
    user_columns = {row["name"] for row in db.execute("PRAGMA table_info(users)")}
    for column in ("must_change_password", "reset_requested"):
        if column not in user_columns:
            db.execute(f"ALTER TABLE users ADD COLUMN {column} INTEGER NOT NULL DEFAULT 0")
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY,
            module TEXT NOT NULL,
            data TEXT NOT NULL,
            created_by INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    db.execute("CREATE INDEX IF NOT EXISTS records_module ON records (module)")
    g.db = db
    return db


@app.teardown_appcontext
def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def users_exist():
    with get_db() as db:
        return db.execute("SELECT 1 FROM users LIMIT 1").fetchone() is not None


def csrf_token():
    token = session.get("_csrf_token")
    if token is None:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


def can_edit(user):
    return bool(user) and (user["is_admin"] or user["role"] in ("Gestor de frota", "Operador"))


def can_delete(user):
    return bool(user) and (user["is_admin"] or user["role"] == "Gestor de frota")


@app.context_processor
def inject_template_helpers():
    vehicle_count = None
    if g.get("user") is not None:
        with get_db() as db:
            vehicle_count = db.execute(
                "SELECT COUNT(*) FROM records WHERE module = 'veiculos'"
            ).fetchone()[0]
    return {"csrf_token": csrf_token, "vehicle_count": vehicle_count}


@app.before_request
def load_logged_in_user():
    user_id = session.get("user_id")
    g.user = None
    if user_id is not None:
        with get_db() as db:
            g.user = db.execute(
                "SELECT id, name, email, role, is_admin, must_change_password FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
        if g.user is None:
            session.clear()
    if request.method == "POST":
        submitted = request.form.get("csrf_token", "")
        if not submitted or not hmac.compare_digest(submitted, session.get("_csrf_token", "")):
            abort(400, description="Token de segurança inválido. Atualize a página e tente novamente.")
    if (
        g.user is not None
        and g.user["must_change_password"]
        and request.endpoint not in PASSWORD_CHANGE_ENDPOINTS
    ):
        return redirect(url_for("change_password"))


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for("setup" if not users_exist() else "login"))
        return view(**kwargs)

    return wrapped_view


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped_view(**kwargs):
        if not g.user["is_admin"]:
            abort(403)
        return view(**kwargs)

    return wrapped_view


def valid_password(password):
    if not PASSWORD_MIN <= len(password) <= PASSWORD_MAX:
        return f"A senha deve ter de {PASSWORD_MIN} a {PASSWORD_MAX} caracteres."
    return None


def valid_account(name, email, password):
    if len(name.strip()) < 2:
        return "Informe o nome completo."
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        return "Informe um e-mail válido."
    return valid_password(password)


def summarize_dashboard(db):
    today = date.today()
    vehicles = [r["data"] for r in load_records(db, "veiculos") if r["data"].get("status") != "Vendido"]
    status = Counter(v.get("status") for v in vehicles)
    total = len(vehicles)

    deadlines = []
    sources = (
        ("manutencoes", "Manutenção", "previsao", "descricao"),
        ("licenciamentos", "Licenciamento", "vencimento", None),
        ("seguros", "Seguro", "vigencia", None),
    )
    open_maintenance = 0
    preventive = 0
    km_alerts = []
    seguro_alerts = []
    for key, label, date_field, detail_field in sources:
        for rec in load_records(db, key):
            d = rec["data"]
            if key == "manutencoes":
                alert = km_alert(d)
                if alert:
                    km_alerts.append({**alert, "placa": d["placa"]})
                if d.get("status") in ("Concluída", "Cancelada"):
                    continue
                open_maintenance += 1
                preventive += d.get("tipo") == "Preventiva"
            elif key == "seguros":
                alert = seguro_alert(d)
                if alert:
                    seguro_alerts.append({**alert, "placa": d["placa"]})
                if d.get("status") in ("Renovada", "Cancelada"):
                    continue
            elif d.get("status") in ("Cancelada",):
                continue
            if not d.get(date_field):
                continue
            due = date.fromisoformat(d[date_field])
            days = (due - today).days
            if days < 0:
                when = f"venceu há {-days} dia(s)"
            elif days == 0:
                when = "vence hoje"
            else:
                when = f"vence em {days} dia(s)"
            deadlines.append(
                {
                    "label": label,
                    "placa": d.get("placa"),
                    "due": due,
                    "days": days,
                    "when": when,
                    "day": f"{due.day:02d}",
                    "month": MONTHS[due.month - 1],
                    "tone": "red" if days <= 7 else "blue",
                }
            )
    deadlines.sort(key=lambda item: item["due"])

    movements = [r["data"] for r in load_records(db, "movimentacoes")]
    fleet = fleet_numbers(db)
    for m in movements:
        m["frota"] = fleet.get(m.get("placa"))
    movements.sort(key=lambda m: m.get("data") or "", reverse=True)

    return {
        "total": total,
        "em_operacao": status["Em operação"],
        "disponiveis": status["Disponível"],
        "em_manutencao": status["Em manutenção"],
        "percent_operacao": round(100 * status["Em operação"] / total) if total else 0,
        "manutencoes_abertas": open_maintenance,
        "preventivas": preventive,
        "alertas": sum(1 for item in deadlines if item["days"] <= 30 and item["label"] != "Seguro")
        + len(km_alerts)
        + len(seguro_alerts),
        "km_alerts": sorted(km_alerts, key=lambda a: a["level"] != "over"),
        "seguro_alerts": sorted(seguro_alerts, key=lambda a: a["level"] != "over"),
        "deadlines": deadlines[:5],
        "movements": movements[:5],
        "today": f"{WEEKDAYS[today.weekday()]}, {today.day} de {MONTH_NAMES[today.month - 1]} de {today.year}",
    }


@app.route("/")
def home():
    if g.user is None:
        return redirect(url_for("setup" if not users_exist() else "login"))
    with get_db() as db:
        users = db.execute(
            "SELECT id, name, email, role, is_admin, last_seen, reset_requested FROM users ORDER BY name COLLATE NOCASE"
        ).fetchall()
        summary = summarize_dashboard(db)
    return render_template(
        "Dashboard.HTML",
        summary=summary,
        users=users,
        current_user=g.user,
    )


@app.route("/setup", methods=("GET", "POST"))
def setup():
    if users_exist():
        return redirect(url_for("home") if g.user else url_for("login"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        error = valid_account(name, email, password)
        if error:
            flash(error, "error")
        else:
            try:
                with get_db() as db:
                    cursor = db.execute(
                        "INSERT INTO users (name, email, password_hash, role, is_admin) VALUES (?, ?, ?, ?, 1)",
                        (name, email, generate_password_hash(password), "Administrador"),
                    )
                session.clear()
                session["user_id"] = cursor.lastrowid
                flash("Administrador criado. Acesso liberado.", "success")
                return redirect(url_for("home"))
            except sqlite3.IntegrityError:
                flash("Não foi possível criar o administrador. Atualize a página e tente novamente.", "error")
    return render_template("auth.html", mode="setup")


def login_locked(key):
    now = time.time()
    attempts = [t for t in LOGIN_FAILS.get(key, []) if now - t < LOGIN_LOCK_SECONDS]
    if attempts:
        LOGIN_FAILS[key] = attempts
    else:
        LOGIN_FAILS.pop(key, None)
    return len(attempts) >= LOGIN_MAX_FAILS


@app.route("/login", methods=("GET", "POST"))
def login():
    if not users_exist():
        return redirect(url_for("setup"))
    if g.user is not None:
        return redirect(url_for("home"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        key = (request.remote_addr, email)
        if login_locked(key):
            flash("Muitas tentativas incorretas. Aguarde 15 minutos e tente novamente.", "error")
            return render_template("auth.html", mode="login")
        with get_db() as db:
            user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            if user and check_password_hash(user["password_hash"], password):
                LOGIN_FAILS.pop(key, None)
                db.execute("UPDATE users SET last_seen = CURRENT_TIMESTAMP WHERE id = ?", (user["id"],))
                session.clear()
                session["user_id"] = user["id"]
                csrf_token()
                return redirect(url_for("home"))
        LOGIN_FAILS.setdefault(key, []).append(time.time())
        flash("E-mail ou senha incorretos.", "error")
    return render_template("auth.html", mode="login")


@app.route("/esqueci-senha", methods=("GET", "POST"))
def forgot_password():
    if g.user is not None:
        return redirect(url_for("change_password"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        with get_db() as db:
            db.execute("UPDATE users SET reset_requested = 1 WHERE email = ?", (email,))
        flash(
            "Solicitação enviada. Se o e-mail estiver cadastrado, o administrador receberá o pedido "
            "e informará uma senha temporária.",
            "success",
        )
        return redirect(url_for("login"))
    return render_template("forgot.html")


@app.route("/conta/senha", methods=("GET", "POST"))
@login_required
def change_password():
    forced = bool(g.user["must_change_password"])
    if request.method == "POST":
        current = request.form.get("current_password", "")
        new = request.form.get("new_password", "")
        confirm = request.form.get("confirm_password", "")
        with get_db() as db:
            row = db.execute("SELECT password_hash FROM users WHERE id = ?", (g.user["id"],)).fetchone()
            error = None
            if not check_password_hash(row["password_hash"], current):
                error = "A senha atual está incorreta."
            elif valid_password(new):
                error = valid_password(new)
            elif new != confirm:
                error = "A confirmação não confere com a nova senha."
            elif new == current:
                error = "A nova senha deve ser diferente da atual."
            if error:
                flash(error, "error")
            else:
                db.execute(
                    "UPDATE users SET password_hash = ?, must_change_password = 0, reset_requested = 0 WHERE id = ?",
                    (generate_password_hash(new), g.user["id"]),
                )
                flash("Senha alterada com sucesso.", "success")
                return redirect(url_for("home"))
    return render_template("password.html", forced=forced, current_user=g.user)


@app.post("/logout")
@login_required
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.post("/users")
@admin_required
def create_user():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    role = request.form.get("role", "")
    error = valid_account(name, email, password)
    if error:
        flash(error, "error")
    elif role not in ROLES:
        flash("Selecione um perfil de acesso válido.", "error")
    else:
        try:
            with get_db() as db:
                db.execute(
                    "INSERT INTO users (name, email, password_hash, role, must_change_password) VALUES (?, ?, ?, ?, 1)",
                    (name, email, generate_password_hash(password), role),
                )
            flash(f"Acesso criado para {name}. Ele deverá trocar a senha no primeiro acesso.", "success")
        except sqlite3.IntegrityError:
            flash("Já existe um acesso cadastrado com esse e-mail.", "error")
    return redirect(url_for("home") + "#usuarios")


@app.post("/users/<int:user_id>/reset-password")
@admin_required
def reset_user_password(user_id):
    if user_id == g.user["id"]:
        flash("Use a opção \"Alterar senha\" para trocar a sua própria senha.", "error")
        return redirect(url_for("home") + "#usuarios")
    temp = "".join(secrets.choice(TEMP_PASSWORD_ALPHABET) for _ in range(PASSWORD_MAX))
    with get_db() as db:
        user = db.execute("SELECT name FROM users WHERE id = ?", (user_id,)).fetchone()
        if user is None:
            abort(404)
        db.execute(
            "UPDATE users SET password_hash = ?, must_change_password = 1, reset_requested = 0 WHERE id = ?",
            (generate_password_hash(temp), user_id),
        )
    flash(
        f"Senha temporária de {user['name']}: {temp} — informe ao usuário. "
        "Ela será trocada no próximo acesso e não será exibida novamente.",
        "success",
    )
    return redirect(url_for("home") + "#usuarios")


def get_module(key):
    module = MODULES.get(key)
    if module is None:
        abort(404)
    return module


def load_records(db, key):
    rows = db.execute(
        "SELECT id, data FROM records WHERE module = ? ORDER BY id DESC", (key,)
    ).fetchall()
    return [{"id": row["id"], "data": json.loads(row["data"])} for row in rows]


def vehicle_plates(db):
    return [rec["data"]["placa"] for rec in reversed(load_records(db, "veiculos"))]


def fleet_numbers(db):
    return {rec["data"]["placa"]: rec["data"].get("frota") for rec in load_records(db, "veiculos")}


def plate_in_use(db, plate, ignore_id=None):
    return any(
        rec["data"]["placa"] == plate and rec["id"] != ignore_id
        for rec in load_records(db, "veiculos")
    )


def set_vehicle_status(db, plate, status, only_if=None):
    for rec in load_records(db, "veiculos"):
        d = rec["data"]
        if d["placa"] == plate and (only_if is None or d.get("status") == only_if):
            d["status"] = status
            db.execute(
                "UPDATE records SET data = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (json.dumps(d, ensure_ascii=False), rec["id"]),
            )


def sellable_plates(db, current_plate=None):
    """Placas de veículos ainda não vendidos (mais a da venda em edição)."""
    sold = {rec["data"]["placa"] for rec in load_records(db, "vendas")}
    sold.discard(current_plate)
    return [p for p in vehicle_plates(db) if p not in sold]


@app.get("/m/<key>")
@login_required
def module_list(key):
    module = get_module(key)
    with get_db() as db:
        records = load_records(db, key)
        plates = sorted(vehicle_plates(db))
        if key == "vendas":
            plates = sorted(sellable_plates(db))
        fleet = fleet_numbers(db)
    alerts = []
    alert_fn = ALERTS.get(key)
    if alert_fn:
        for rec in records:
            alert = alert_fn(rec["data"])
            if alert:
                rec["alert"] = alert
                alerts.append({**alert, "placa": rec["data"]["placa"]})
        alerts.sort(key=lambda a: a["level"] != "over")
    return render_template(
        "module.html",
        key=key,
        module=module,
        records=records,
        plates=plates,
        fleet=fleet,
        alerts=alerts,
        current_user=g.user,
        can_edit=can_edit(g.user),
        can_delete=can_delete(g.user),
    )


def km_alert(data_):
    """Alerta de revisão preventiva por km, ou None quando não se aplica."""
    if data_.get("tipo") != "Preventiva" or data_.get("status") in ("Concluída", "Cancelada"):
        return None
    atual, revisao = data_.get("km_atual"), data_.get("km_revisao")
    if atual is None or revisao is None:
        return None
    restante = revisao - atual
    if restante < 0:
        return {"level": "over", "text": f"revisão ultrapassada em {num(-restante)} km"}
    if restante <= KM_WARNING:
        return {"level": "soon", "text": f"faltam {num(restante)} km para a revisão"}
    return None


def seguro_alert(data_):
    """Alerta de renovação de seguro por prazo, ou None quando não se aplica."""
    if data_.get("status") in ("Renovada", "Cancelada") or not data_.get("vigencia"):
        return None
    days = (date.fromisoformat(data_["vigencia"]) - date.today()).days
    if days < 0:
        return {"level": "over", "text": f"seguro vencido há {-days} dia(s), renovação necessária"}
    if days <= SEGURO_WARNING_DAYS:
        when = "vence hoje" if days == 0 else f"vence em {days} dia(s)"
        return {"level": "soon", "text": f"renovação do seguro: {when}"}
    return None


ALERTS = {"manutencoes": km_alert, "seguros": seguro_alert}


def previous_plate(db, key, record_id):
    if record_id is None:
        return None
    row = db.execute("SELECT data FROM records WHERE id = ? AND module = ?", (record_id, key)).fetchone()
    return json.loads(row["data"]).get("placa") if row else None


def save_record(key, record_id=None):
    module = get_module(key)
    if not can_edit(g.user):
        abort(403)
    with get_db() as db:
        data_, error = clean_record(module, request.form, vehicle_plates(db))
        if not error and key == "manutencoes" and data_["tipo"] == "Preventiva":
            if data_["km_atual"] is None or data_["km_revisao"] is None:
                error = "Na manutenção preventiva, informe o km atual e o km da revisão."
        if not error and key == "veiculos" and plate_in_use(db, data_["placa"], record_id):
            error = "Já existe um veículo cadastrado com essa placa."
        if not error and key == "vendas" and data_["placa"] not in sellable_plates(
            db, previous_plate(db, key, record_id)
        ):
            error = "Esse veículo já tem uma venda registrada."
        if not error and record_id is not None:
            exists = db.execute(
                "SELECT 1 FROM records WHERE id = ? AND module = ?", (record_id, key)
            ).fetchone()
            if not exists:
                abort(404)
        if error:
            flash(error, "error")
        elif record_id is None:
            db.execute(
                "INSERT INTO records (module, data, created_by) VALUES (?, ?, ?)",
                (key, json.dumps(data_, ensure_ascii=False), g.user["id"]),
            )
            if key == "vendas":
                set_vehicle_status(db, data_["placa"], "Vendido")
            flash(f"Cadastro de {module['singular']} salvo.", "success")
        else:
            old_plate = previous_plate(db, key, record_id)
            db.execute(
                "UPDATE records SET data = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND module = ?",
                (json.dumps(data_, ensure_ascii=False), record_id, key),
            )
            if key == "vendas" and old_plate != data_["placa"]:
                set_vehicle_status(db, old_plate, "Disponível", only_if="Vendido")
                set_vehicle_status(db, data_["placa"], "Vendido")
            flash(f"Dados do {module['singular']} atualizados.", "success")
    return redirect(url_for("module_list", key=key))


@app.post("/m/<key>")
@login_required
def module_create(key):
    return save_record(key)


@app.post("/m/<key>/<int:record_id>")
@login_required
def module_update(key, record_id):
    return save_record(key, record_id)


@app.post("/m/<key>/<int:record_id>/delete")
@login_required
def module_delete(key, record_id):
    module = get_module(key)
    if not can_delete(g.user):
        abort(403)
    with get_db() as db:
        if key == "vendas":
            set_vehicle_status(db, previous_plate(db, key, record_id), "Disponível", only_if="Vendido")
        db.execute("DELETE FROM records WHERE id = ? AND module = ?", (record_id, key))
    flash(f"Registro de {module['singular']} excluído.", "success")
    return redirect(url_for("module_list", key=key))


@app.route("/health")
def health():
    return jsonify(status="ok")


@app.template_filter("brl")
def brl(value):
    return "R$ " + f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


@app.template_filter("fmtvalue")
def fmtvalue(value, kind):
    if value is None or value == "":
        return "—"
    if kind == "money":
        return brl(value)
    if kind == "int":
        return num(value)
    if kind == "date":
        y, m, d = value.split("-")
        return f"{d}/{m}/{y}"
    if kind == "datetime":
        day, _, hour = value.partition("T")
        y, m, d = day.split("-")
        return f"{d}/{m}/{y} {hour}"
    return value


@app.template_filter("num")
def num(value):
    return f"{value:,}".replace(",", ".")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
