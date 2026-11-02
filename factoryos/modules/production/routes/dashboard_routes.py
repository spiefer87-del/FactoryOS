from flask import render_template, request
from flask_login import login_required,current_user
from factoryos.core.auth import has_permission
from factoryos.modules.production.services.order_statistics import local_label

from factoryos.modules.production.services.timeline_service import get_machine_timeline

from . import bp


@bp.route("/")
@login_required
def dashboard():

    return render_template(
        "production/dashboard.html"
    )


@bp.route("/booking")
@login_required
def booking_dashboard():
    timeline = get_machine_timeline(request.args.get("zeitraum", "24h"))
    return render_template(
        "production/booking/dashboard.html",
        **timeline,
        can_correct_time=has_permission(current_user,"production.edit_booking_time"),
        local_label=local_label,
    )
