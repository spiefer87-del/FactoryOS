from factoryos.modules.admin.roles.models import Role


def get_all_roles():
    return Role.query.order_by(Role.name).all()


def get_role(role_id):
    return Role.query.get_or_404(role_id)


def get_role_by_name(name):
    return Role.query.filter_by(name=name).first()
