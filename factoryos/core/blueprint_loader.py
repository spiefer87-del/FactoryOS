import importlib
import pkgutil


def load_blueprints(app):

    import factoryos.modules

    for loader, name, is_pkg in pkgutil.walk_packages(
        factoryos.modules.__path__,
        factoryos.modules.__name__ + "."
    ):

        # nur routes packages laden
        if name.endswith(".routes"):

            print("Loading:", name)

            module = importlib.import_module(name)

            if hasattr(module, "bp"):
                print("Registering:", module.bp.name)
                app.register_blueprint(module.bp)
