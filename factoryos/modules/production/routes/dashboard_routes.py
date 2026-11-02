from flask import render_template, request
from flask_login import login_required,current_user
from factoryos.core.auth import has_permission
from factoryos.modules.production.services.order_statistics import local_label,local_time

from factoryos.modules.production.services.timeline_service import get_machine_timeline,parse_timeline_range,HORIZONS

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
    selected=request.args.get("zeitraum","24h")
    error=None
    try:
        if selected=="custom":
            start,end=parse_timeline_range(request.args.get("von",""),request.args.get("bis",""),
                request.args.get("von_fold",""),request.args.get("bis_fold",""))
            timeline=get_machine_timeline("custom",range_start=start,range_end=end)
        else:timeline=get_machine_timeline(selected)
    except ValueError as exc:
        error=str(exc)+" Angezeigt werden vorläufig 24 Stunden um jetzt; bitte Eingabe korrigieren."
        timeline=get_machine_timeline()
    if selected not in HORIZONS and selected!="custom":selected="24h"
    return render_template(
        "production/booking/dashboard.html",
        **timeline,
        can_correct_time=has_permission(current_user,"production.edit_booking_time"),
        local_label=local_label,
        selected_horizon=selected,range_error=error,
        custom_start=request.args.get("von",local_time(timeline["range_start"]).strftime("%Y-%m-%dT%H:%M")),
        custom_end=request.args.get("bis",local_time(timeline["range_end"]).strftime("%Y-%m-%dT%H:%M")),
    ),400 if error else 200
