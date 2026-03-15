from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required
from factoryos.extensions import db

from factoryos.modules.admin.roles.models import Role
from factoryos.modules.admin.permissions.models import Permission

from . import bp


@bp.route("/roles/<int:role_id>", methods=["GET", "POST"])
@login_required
def role_permissions(role_id):

    role = Role.query.get_or_404(role_id)

    permissions = Permission.query.order_by(Permission.name).all()

    if request.method == "POST":

        selected_permissions = request.form.getlist("permissions")

        role.permissions = Permission.query.filter(
            Permission.id.in_(selected_permissions)
        ).all()

        db.session.commit()

        flash("Rechte aktualisiert", "success")

        return redirect(url_for("admin_roles.list_roles"))

    return render_template(
        "admin/roles/permissions.html",
        role=role,
        permissions=permissions
    )