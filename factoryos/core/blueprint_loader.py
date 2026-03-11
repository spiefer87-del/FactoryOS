import importlib
import pkgutil


def load_blueprints(app):

    import factoryos.modules

    def walk_packages(package):

        for loader, name, is_pkg in pkgutil.walk_packages(package.__path__, package.__name__ + "."):

            if name.endswith(".routes"):

                module = importlib.import_module(name)

                if hasattr(module, "bp"):

                    app.register_blueprint(module.bp)

    walk_packages(factoryos.modules)
