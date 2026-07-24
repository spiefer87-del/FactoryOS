from flask import render_template
from flask_login import login_required, current_user

from factoryos.core.auth import has_permission

from . import bp


@bp.route("/")
@login_required
def dashboard():

    return render_template(
        "masterdata/tools/dashboard.html",

        can_export_tools_excel=has_permission(
            current_user,
            "tools.excel_export"
        )
    )
