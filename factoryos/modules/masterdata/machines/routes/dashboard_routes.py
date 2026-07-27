from flask import render_template
from flask_login import login_required, current_user

from factoryos.core.auth import (
    permission_required,
    has_permission
)

from . import bp


@bp.route("/")
@login_required
@permission_required("machines.view")
def dashboard():

    return render_template(
        "masterdata/machines/dashboard.html",

        can_create_machine=has_permission(
            current_user,
            "machines.create"
        ),

        can_edit_machines=has_permission(
            current_user,
            "machines.edit"
        ),

        can_import_machines=has_permission(
            current_user,
            "machines.excel_import"
        ),

        can_export_machines=has_permission(
            current_user,
            "machines.excel_export"
        )
    )
