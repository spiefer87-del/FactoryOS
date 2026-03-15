# edit_routes.py

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required

from factoryos.modules.admin.roles.queries.role_queries import get_role
from factoryos.modules.admin.roles.services.role_service import update_role

from .role_routes import bp


@bp.route("/edit/<int:role_id>", methods=["GET", "POST"])
@login_required
def edit_role(role_id):

    role = get_role(role_id)

    if request.method == "POST":

        name = request.form.get("name")
        description = request.form.get("description")
        active = request.form.get("active") == "1"

        update_role(role, name, description, active)

        flash("Rolle aktualisiert", "success")

        return redirect(url_for("admin_roles.list_roles"))

    return render_template(
        "admin/roles/edit.html",
        role=role
    )