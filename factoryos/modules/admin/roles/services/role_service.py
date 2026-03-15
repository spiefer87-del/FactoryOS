from factoryos.extensions import db
from factoryos.modules.admin.roles.models import Role


def create_role(name, description):

    role = Role(
        name=name,
        description=description
    )

    db.session.add(role)
    db.session.commit()

    return role


def update_role(role, name, description, active):

    role.name = name
    role.description = description
    role.active = active

    db.session.commit()

    return role


def delete_role(role):

    db.session.delete(role)
    db.session.commit()
