import importlib
import pkgutil


def register_blueprints(app):

    package = "factoryos.modules"

    for importer, module_name, is_pkg in pkgutil.walk_packages(
        path=__import__(package).__path__,
        prefix=package + ".",
        onerror=lambda x: None,
    ):

        if module_name.endswith(".routes"):

            module = importlib.import_module(module_name)

            for attr in dir(module):

                obj = getattr(module, attr)

                try:
                    from flask import Blueprint

                    if isinstance(obj, Blueprint):
                        app.register_blueprint(obj)

                except:
                    pass