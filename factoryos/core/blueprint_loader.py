import importlib
import pkgutil


def load_blueprints(app):

    import factoryos.modules

    package = factoryos.modules

    for _, module_name, _ in pkgutil.iter_modules(package.__path__):

        module_path = f"factoryos.modules.{module_name}"

        try:

            routes_module = importlib.import_module(f"{module_path}.routes")

            if hasattr(routes_module, "bp"):
                app.register_blueprint(routes_module.bp)

        except ModuleNotFoundError:
            pass
