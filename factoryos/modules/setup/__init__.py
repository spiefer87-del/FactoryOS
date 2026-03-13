from factoryos.modules.setup.machines.routes import machine_bp


def register_setup(app):

    app.register_blueprint(machine_bp)
