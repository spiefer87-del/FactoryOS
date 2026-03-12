from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import func

from factoryos.extensions import db
from factoryos.models.machine import Machine
from factoryos.modules.production.models import TimeBooking, QuantityReport, DowntimeReason

bp = Blueprint(
    "production_dashboard",
    __name__,
    url_prefix="/production"
)

@bp.route("/dashboard")
@login_required
def dashboard():

    machines = (
        Machine.query
        .filter_by(active=True)
        .order_by(Machine.name.asc())
        .all()
    )

    active_bookings = (
        TimeBooking.query
        .filter(TimeBooking.end_time.is_(None))
        .all()
    )

    active_by_machine = {}

    for b in active_bookings:
        if b.machine_id not in active_by_machine:
            active_by_machine[b.machine_id] = b
        else:
            if b.start_time > active_by_machine[b.machine_id].start_time:
                active_by_machine[b.machine_id] = b

    reasons = (
        DowntimeReason.query
        .filter_by(active=True)
        .order_by(DowntimeReason.name.asc())
        .all()
    )

    return render_template(
        "dashboard_machines.html",
        machines=machines,
        active_by_machine=active_by_machine,
        reasons=reasons
    )
