from flask import Flask
from config import Config
from extensions import db, login_manager, migrate
from factoryos.core.blueprint_loader import register_blueprints


def create_app():

    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    # 🔥 automatische Blueprint Registrierung
    register_blueprints(app)

    return app