# create_routes.py

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required

from factoryos.modules.admin.roles.services.role_service import create_role
from factoryos.modules.admin.roles.queries.role_queries import get_role_by_name

from .role_routes import bp


@bp.route("/create", methods=["GET", "POST"])
@login_required
def create_role_route():

    if request.method == "POST":

        name = request.form.get("name")
        description = request.form.get("description")

        existing = get_role_by_name(name)

        if existing:
            flash("Rolle existiert bereits", "error")
            return redirect(url_for("admin_roles.create_role_route"))

        create_role(name, description)

        flash("Rolle erstellt", "success")

        return redirect(url_for("admin_roles.list_roles"))

    return render_template("admin/roles/create.html")