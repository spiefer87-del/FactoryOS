from factoryos.core.services.change_log_service import record_entity, snapshot
from factoryos.extensions import db
from factoryos.modules.admin.roles.models import Role


def create_role(name, description):

    role = Role(
        name=name,
        description=description
    )

    db.session.add(role)
    record_entity(role,"role","create",("name","description","active"))
    db.session.commit()

    return role


def update_role(role, name, description, active):

    before=snapshot(role,("name","description","active"))
    role.name = name
    role.description = description
    role.active = active
    record_entity(role,"role","update",("name","description","active"),before=before)
    db.session.commit()

    return role


def delete_role(role):

    record_entity(role,"role","delete",("name","description","active"))
    db.session.delete(role)
    db.session.commit()
