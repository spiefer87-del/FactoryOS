# role_routes.py

from flask import Blueprint, render_template
from flask_login import login_required

from factoryos.modules.admin.roles.queries.role_queries import get_all_roles

bp = Blueprint(
    "admin_roles",
    __name__,
    url_prefix="/admin/roles"
)


@bp.route("/")
@login_required
def list_roles():

    roles = get_all_roles()

    return render_template(
        "admin/roles/role.html",
        roles=roles
    )