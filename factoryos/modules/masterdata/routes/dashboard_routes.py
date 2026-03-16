from flask import render_template
from flask_login import login_required
from . import bp
from factoryos.modules.masterdata.core.registry import list_masterdata


@bp.route("/dashboard")
@login_required
def dashboard():
    modules = list_masterdata()

    return render_template(
        "masterdata/dashboard.html",
        modules=modules
    )
