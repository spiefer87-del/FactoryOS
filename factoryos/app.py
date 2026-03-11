import os
import openpyxl
import io
from datetime import datetime
from dateutil.relativedelta import relativedelta
from functools import wraps
from sqlalchemy import func, or_
from openpyxl import load_workbook, Workbook
from flask_migrate import Migrate
from io import BytesIO
from openpyxl.utils import get_column_letter
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak, Flowable, KeepTogether
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from PIL import Image as PILImage, ImageDraw, ImageFont
from pdf2image import convert_from_path, convert_from_bytes

from factoryos.models.user import User
from factoryos.models.machine import Machine
from factoryos.models.tools import ToolMasterdata

from factoryos.modules.production.models import *
from factoryos.modules.quality.models import *




BASE_DIR = os.path.abspath(os.path.dirname(__file__))

UPLOAD_DRAWINGS = os.path.join(BASE_DIR, "static", "qm_drawings")
UPLOAD_SNIPPETS = os.path.join(BASE_DIR, "static", "qm_snippets")
UPLOAD_IDENTIFICATION = os.path.join(BASE_DIR, "static", "qm_identification")

app = Flask(__name__)

# SECRET KEY (auf PythonAnywhere wichtig!)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "BITTE_AENDERN_SUPER_SECRET_123")

# DB Pfad absolut setzen (wichtig auf PythonAnywhere)
db_path = os.path.join(BASE_DIR, "bde.db")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + db_path

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
migrate.init_app(app, db)


login_manager.init_app(app)
login_manager.login_view = "login"


# ---------------------------
# Modelle
# ---------------------------











class AppSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    company_name = db.Column(db.String(200), nullable=True)
    company_address = db.Column(db.String(400), nullable=True)

    logo_filename = db.Column(db.String(200), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)



@app.route("/", methods=["GET"])
def root():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


# ---------------------------
# Init (nur einmal ausführen!)
# ---------------------------

@app.route("/init")
def init_db():
    db.create_all()

    if not User.query.filter_by(username="admin").first():
        admin = User(username="admin", role="admin")
        admin.set_password("admin123")
        db.session.add(admin)

    if not Machine.query.first():
        db.session.add(Machine(name="Maschine 1", location="Halle A"))
        db.session.add(Machine(name="Maschine 2", location="Halle A"))

    if not Order.query.first():
        db.session.add(Order(order_no="A-10001", article="Artikel 1", description="Testauftrag", target_qty=1000))
        db.session.add(Order(order_no="A-10002", article="Artikel 2", description="Testauftrag", target_qty=500))

    if not DowntimeReason.query.first():
        db.session.add(DowntimeReason(name="Material fehlt"))
        db.session.add(DowntimeReason(name="Werkzeug defekt"))
        db.session.add(DowntimeReason(name="Warten auf QS"))

    if not ToolErrorTitlePreset.query.first():
        presets = [
            "Angußbuchse defekt",
            "Auswerfer defekt",
            "Kühlung defekt",
            "Düse undicht",
            "Werkzeug schließt nicht",
            "Werkzeug öffnet nicht",
            "Gratbildung",
            "Kernzug defekt",
            "Heißkanal defekt",
            "Sensor defekt",
        ]

        for i, t in enumerate(presets, start=1):
            db.session.add(ToolErrorTitlePreset(title=t, sort_order=i, active=True))



    db.session.commit()
    return render_template("admin_seed.html")


# ---------------------------
# Auth
# ---------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        user = User.query.filter_by(username=username, active=True).first()

        if not user or not user.check_password(password):
            flash("Login fehlgeschlagen.", "danger")
            return redirect(url_for("login"))

        login_user(user)
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


















################################################SETUP#############################



from sqlalchemy import event
from sqlalchemy.engine import Engine
import sqlite3

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()



# WICHTIG:
# Kein app.run() bei PythonAnywhere


