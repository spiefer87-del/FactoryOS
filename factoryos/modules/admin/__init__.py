from factoryos.modules.admin.users.routes.user_routes import bp as users_bp


def register_admin(app):

    app.register_blueprint(users_bp)
