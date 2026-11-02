"""Legacy starts/stops open the machine panel instead of silently replacing work."""
from flask import redirect, url_for, request, render_template, abort
from flask_login import login_required
from factoryos.models.machine import Machine
from factoryos.modules.production.models import TimeBooking
from factoryos.modules.production.services.booking_service import get_manual_start_data
from . import bp

def _selection():
    machine_id=request.form.get("machine_id",type=int) or request.args.get("machine_id",type=int)
    order_id=request.form.get("order_id",type=int) or request.args.get("order_id",type=int)
    if machine_id:
        Machine.query.get_or_404(machine_id)
        return redirect(url_for("production.machine_control",machine_id=machine_id,order_id=order_id),code=303)
    return render_template("production/booking/manual_start.html",**get_manual_start_data(),
        selected_order_id=order_id,selected_machine_id=None,comment="")

@bp.route("/booking/start",methods=["GET","POST"])
@login_required
def manual_start():
    return _selection()

@bp.route("/start",methods=["POST"])
@login_required
def start_booking():
    return _selection()

def _booking_panel(booking_id):
    booking=TimeBooking.query.get_or_404(booking_id)
    if not booking.machine_id:abort(400,"Keine Maschinenbuchung.")
    return redirect(url_for("production.machine_control",machine_id=booking.machine_id),code=303)

@bp.route("/end/<int:booking_id>",methods=["POST"])
@login_required
def end_booking_route(booking_id):
    return _booking_panel(booking_id)

@bp.route("/resume/<int:booking_id>",methods=["POST"])
@login_required
def resume_from_pause_or_downtime(booking_id):
    return _booking_panel(booking_id)
