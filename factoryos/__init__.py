from flask import Flask

from .config import Config
from .extensions import db, login_manager

from .core.blueprint_loader import load_blueprints


def create_app():

    app = Flask(__name__)

    # ------------------------
    # CONFIG
    # ------------------------

    app.config.from_object(Config)

    # ------------------------
    # EXTENSIONS
    # ------------------------

    db.init_app(app)
    login_manager.init_app(app)

    # ------------------------
    # BLUEPRINT AUTO LOADER
    # ------------------------

    load_blueprints(app)

    return app
