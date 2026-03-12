from .routes import blueprints

from factoryos.modules.projects import blueprints as project_bps

for bp in project_bps:
    app.register_blueprint(bp)
