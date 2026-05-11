"""
SySM Quiz  —  Flask web app with login and leaderboard
Environment variables required:
  DATABASE_URL  – PostgreSQL connection string
  SECRET_KEY    – (optional) Flask secret; random fallback used if absent
Run locally : python app.py
Production  : gunicorn app:app
"""
import json
import os
import random
from datetime import datetime

from flask import (Flask, abort, flash, jsonify, redirect,
                   render_template, request, url_for)
from flask_login import (LoginManager, UserMixin, current_user,
                         login_required, login_user, logout_user)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

# ── App setup ─────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

TOPICS = [
    {"id": "cinematica",   "name": "Modelado y simulación cinemática"},
    {"id": "dinamica",     "name": "Modelado y simulación dinámica"},
    {"id": "control",      "name": "Simulación con control"},
    {"id": "sensibilidad", "name": "Análisis de sensibilidad cinemática"},
    {"id": "sintesis",     "name": "Síntesis dimensional de mecanismos"},
    {"id": "integradores", "name": "Comparativa de integradores numéricos"},
]
TOPIC_IDS = {t["id"] for t in TOPICS}

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(32)

# ── Database ──────────────────────────────────────────────
db_url = os.environ.get("DATABASE_URL", "")
if db_url.startswith("postgres://"):          # Railway / Heroku legacy prefix
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = db_url or "sqlite:///sysm_local.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Inicia sesión para guardar tu puntuación."

# ── Models ────────────────────────────────────────────────
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id           = db.Column(db.Integer, primary_key=True)
    username     = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    scores       = db.relationship("Score", backref="user", lazy=True)

    def set_password(self, pw: str) -> None:
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw: str) -> bool:
        return check_password_hash(self.password_hash, pw)


class Score(db.Model):
    __tablename__ = "scores"
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    topic_id   = db.Column(db.String(40), nullable=False)
    correct    = db.Column(db.Integer, nullable=False)
    total      = db.Column(db.Integer, nullable=False)
    played_at  = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def pct(self) -> int:
        return round(self.correct / self.total * 100) if self.total else 0


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ── Helpers ───────────────────────────────────────────────
def load_bank(topic_id: str):
    path = os.path.join(DATA_DIR, f"{topic_id}.json")
    if not os.path.isfile(path):
        abort(404)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Routes — main ─────────────────────────────────────────
@app.route("/")
def index():
    counts = {}
    for t in TOPICS:
        path = os.path.join(DATA_DIR, f"{t['id']}.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                counts[t["id"]] = len(json.load(f))
        except Exception:
            counts[t["id"]] = 0
    return render_template("index.html", topics=TOPICS, counts=counts)


@app.route("/test/<topic_id>")
def test_view(topic_id):
    topic = next((t for t in TOPICS if t["id"] == topic_id), None)
    if topic is None:
        abort(404)
    return render_template("test.html", topic=topic)


# ── Routes — API ──────────────────────────────────────────
@app.route("/api/test/<topic_id>")
def api_test(topic_id):
    bank = load_bank(topic_id)
    n = min(14, len(bank))
    sample = random.sample(bank, n)
    out = []
    for q in sample:
        opts = list(enumerate(q["options"]))
        random.shuffle(opts)
        new_options = [o[1] for o in opts]
        new_answer = next(i for i, (orig, _) in enumerate(opts) if orig == q["answer"])
        out.append({"q": q["q"], "options": new_options, "answer": new_answer})
    return jsonify(out)


@app.route("/api/score", methods=["POST"])
@login_required
def api_score():
    data = request.get_json(silent=True) or {}
    topic_id = str(data.get("topic_id", ""))
    try:
        correct = int(data.get("correct", 0))
        total   = int(data.get("total", 14))
    except (TypeError, ValueError):
        return jsonify({"error": "invalid payload"}), 400
    if topic_id not in TOPIC_IDS:
        return jsonify({"error": "invalid topic"}), 400
    score = Score(user_id=current_user.id,
                  topic_id=topic_id,
                  correct=correct,
                  total=total)
    db.session.add(score)
    db.session.commit()
    return jsonify({"ok": True, "pct": score.pct})


# ── Routes — leaderboard ──────────────────────────────────
@app.route("/leaderboard")
def leaderboard():
    from sqlalchemy import func
    boards = {}
    for t in TOPICS:
        sub = (
            db.session.query(
                Score.user_id,
                func.max(Score.correct * 100 / Score.total).label("best_pct"),
                func.max(Score.correct).label("best_correct"),
            )
            .filter(Score.topic_id == t["id"])
            .group_by(Score.user_id)
            .subquery()
        )
        rows = (
            db.session.query(User.username, sub.c.best_pct, sub.c.best_correct)
            .join(sub, User.id == sub.c.user_id)
            .order_by(sub.c.best_pct.desc(), sub.c.best_correct.desc())
            .limit(10)
            .all()
        )
        boards[t["id"]] = [
            {"username": r.username, "pct": r.best_pct, "correct": r.best_correct}
            for r in rows
        ]
    return render_template("leaderboard.html", topics=TOPICS, boards=boards)


# ── Routes — auth ─────────────────────────────────────────
@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm", "")
        if not username or not password:
            error = "Completa todos los campos."
        elif len(username) < 3:
            error = "El nombre de usuario debe tener al menos 3 caracteres."
        elif len(password) < 6:
            error = "La contraseña debe tener al menos 6 caracteres."
        elif password != confirm:
            error = "Las contraseñas no coinciden."
        elif User.query.filter_by(username=username).first():
            error = "Ese nombre de usuario ya está en uso."
        else:
            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for("index"))
    return render_template("register.html", error=error)


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user, remember=True)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("index"))
        error = "Usuario o contraseña incorrectos."
    return render_template("login.html", error=error)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


# ── Init ──────────────────────────────────────────────────
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
