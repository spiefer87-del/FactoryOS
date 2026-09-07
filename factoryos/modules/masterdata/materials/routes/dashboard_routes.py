from flask import render_template
from flask_login import current_user, login_required

from factoryos.core.auth import has_permission, permission_required

from . import bp


@bp.route("/")
@login_required
@permission_required("materials.view")
def dashboard():
    return render_template(
        "masterdata/materials/dashboard.html",
        can_create=has_permission(current_user, "materials.create"),
        can_edit=has_permission(current_user, "materials.edit"),
        can_import=has_permission(current_user, "materials.excel_import"),
        can_export=has_permission(current_user, "materials.excel_export"),
    )
