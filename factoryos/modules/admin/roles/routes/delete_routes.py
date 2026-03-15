# delete_routes.py

from flask import redirect, url_for, flash
from flask_login import login_required

from factoryos.modules.admin.roles.queries.role_queries import get_role
from factoryos.modules.admin.roles.services.role_service import delete_role

from .role_routes import bp


@bp.route("/delete/<int:role_id>", methods=["POST"])
@login_required
def delete_role_route(role_id):

    role = get_role(role_id)

    delete_role(role)

    flash("Rolle gelöscht", "success")

    return redirect(url_for("admin_roles.list_roles"))