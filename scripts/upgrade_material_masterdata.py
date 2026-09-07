#!/usr/bin/env python3
"""Idempotent production upgrade for the material master-data module."""

from factoryos import create_app
from factoryos.extensions import db
from factoryos.modules.admin.permissions.models import Permission
from factoryos.modules.admin.roles.models import Role
from factoryos.modules.masterdata.materials.models import Material
from factoryos.core.storage import ensure_storage_structure


MATERIAL_PERMISSIONS = (
    "materials.view",
    "materials.create",
    "materials.edit",
    "materials.delete",
    "materials.documents",
    "materials.excel_import",
    "materials.excel_export",
)


def run_upgrade():
    Material.__table__.create(bind=db.engine, checkfirst=True)

    permissions = []
    for name in MATERIAL_PERMISSIONS:
        permission = Permission.query.filter_by(name=name).first()
        if permission is None:
            permission = Permission(name=name)
            db.session.add(permission)
        permissions.append(permission)

    db.session.flush()
    admin_role = Role.query.filter_by(name="admin").first()
    if admin_role is None:
        raise RuntimeError("Die Rolle 'admin' wurde nicht gefunden.")

    assigned = {permission.name for permission in admin_role.permissions}
    for permission in permissions:
        if permission.name not in assigned:
            admin_role.permissions.append(permission)

    ensure_storage_structure()
    db.session.commit()


def main():
    app = create_app()
    with app.app_context():
        run_upgrade()
    print("Materialstamm-Upgrade erfolgreich abgeschlossen.")


if __name__ == "__main__":
    main()
