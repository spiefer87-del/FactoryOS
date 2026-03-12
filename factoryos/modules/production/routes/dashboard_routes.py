from flask import Blueprint, render_template
from flask_login import login_required

from factoryos.modules.production.queries.dashboard_queries import (
    get_dashboard_data
)

bp = Blueprint(
    "production_dashboard",
    __name__,
    url_prefix="/production"
)


@bp.route("/dashboard")
@login_required
def dashboard():

    machines, active_by_machine, qty_by_order, reasons = get_dashboard_data()

    return render_template(
        "dashboard_machines.html",
        machines=machines,
        active_by_machine=active_by_machine,
        qty_by_order=qty_by_order,
        reasons=reasons
    )
