from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required

from factoryos.extensions import db
from factoryos.modules.admin.roles.models import Role
from factoryos.modules.admin.permissions.models import Permission

from . import bp


@bp.route("/matrix", methods=["GET", "POST"])
@login_required
def permission_matrix():

    roles = Role.query.order_by(Role.name).all()
    permissions = Permission.query.order_by(Permission.name).all()

    permission_groups = {}

    for permission in permissions:
        module = permission.name.split(".")[0]

        if module not in permission_groups:
            permission_groups[module] = []

        permission_groups[module].append(permission)

    if request.method == "POST":

        for role in roles:

            selected = request.form.getlist(f"role_{role.id}")

            role.permissions = Permission.query.filter(
                Permission.id.in_(selected)
            ).all()

        db.session.commit()

        flash("Rechte aktualisiert", "success")

        return redirect(url_for("admin_permissions.permission_matrix"))

    return render_template(
        "admin/permissions/matrix.html",
        roles=roles,
        permission_groups=permission_groups
    )