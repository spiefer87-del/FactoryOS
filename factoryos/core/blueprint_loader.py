import importlib
import pkgutil


def load_blueprints(app):

    import factoryos.modules

    for _, name, _ in pkgutil.walk_packages(
        factoryos.modules.__path__,
        factoryos.modules.__name__ + "."
    ):

        if name.endswith(".routes"):

            module = importlib.import_module(name)

            if hasattr(module, "bp"):

                bp = module.bp

                if bp.name not in app.blueprints:
                    app.register_blueprint(bp)
