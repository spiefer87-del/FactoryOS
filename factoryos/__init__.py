from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix



from .config import Config
from .extensions import db, login_manager, migrate

from .core.blueprint_loader import load_blueprints
from .core import routes as core_routes
from .core.db_seed import run_seeds
from .core.storage import ensure_storage_structure, storage_url

def create_app():

    app = Flask(__name__)

    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    app.config.from_object(Config)
    if not app.config.get("SECRET_KEY"):
        raise RuntimeError("Privater Sitzungsschlüssel fehlt. scripts/configure_session_secret.py ausführen oder FACTORYOS_SECRET_KEY konfigurieren.")

    app.jinja_env.globals["storage_url"] = storage_url

    with app.app_context():
        ensure_storage_structure()

    db.init_app(app)
        
    login_manager.init_app(app)
    migrate.init_app(app, db)
    
    login_manager.login_view = "auth.login"

    # Core routes (Startseite)
    app.register_blueprint(core_routes.bp)

    # Module automatisch laden
    load_blueprints(app)
    from .core.access_control import install_access_control
    install_access_control(app)

    for rule in app.url_map.iter_rules():
        print(rule.endpoint, rule.rule)

    return app
