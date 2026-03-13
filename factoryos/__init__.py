from flask import Flask

from .config import Config
from .extensions import db, login_manager, migrate

from .core.blueprint_loader import load_blueprints


def create_app():

    app = Flask(__name__)

    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    login_manager.login_view = "auth.login"

    load_blueprints(app)

    return app
