from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user

from factoryos.models.machine import Machine
from factoryos.modules.production.models import Order, DowntimeReason
from factoryos.modules.production.services.machine_service import (
    start_setup,
    start_machine_event,
    start_machine_downtime
)

bp = Blueprint(
    "production_machine",
    __name__,
    url_prefix="/production"
)


@bp.route("/machine/<int:machine_id>/setup", methods=["GET", "POST"])
@login_required
def machine_setup(machine_id):

    machine = Machine.query.get_or_404(machine_id)

    orders = (
        Order.query
        .filter(Order.status != "gesperrt")
        .order_by(Order.order_no.asc())
        .all()
    )

    if request.method == "POST":

        start_setup(
            user_id=current_user.id,
            machine_id=machine_id,
            order_id=request.form.get("order_id"),
            mode=request.form.get("mode"),
            tool_no=request.form.get("tool_no"),
            comment=request.form.get("comment")
        )

        flash("Setup gestartet.", "success")

        return redirect(url_for("production_dashboard.dashboard"))

    return render_template(
        "machine_setup.html",
        machine=machine,
        orders=orders
    )


@bp.route("/machine/<int:machine_id>/event", methods=["GET", "POST"])
@login_required
def machine_event(machine_id):

    machine = Machine.query.get_or_404(machine_id)

    if request.method == "POST":

        start_machine_event(
            user_id=current_user.id,
            machine_id=machine_id,
            event=request.form.get("event"),
            comment=request.form.get("comment")
        )

        return redirect(url_for("production_dashboard.dashboard"))

    return render_template(
        "machine_event.html",
        machine=machine
    )


@bp.route("/machine/<int:machine_id>/downtime", methods=["GET", "POST"])
@login_required
def machine_downtime(machine_id):

    machine = Machine.query.get_or_404(machine_id)

    reasons = (
        DowntimeReason.query
        .filter_by(active=True)
        .order_by(DowntimeReason.name.asc())
        .all()
    )

    if request.method == "POST":

        start_machine_downtime(
            user_id=current_user.id,
            machine_id=machine_id,
            reason_id=request.form.get("reason_id"),
            comment=request.form.get("comment")
        )

        return redirect(url_for("production_dashboard.dashboard"))

    return render_template(
        "machine_downtime.html",
        machine=machine,
        reasons=reasons
    )
