from flask import redirect, url_for, request, flash, render_template
from flask_login import login_required, current_user

from factoryos.models.machine import Machine
from factoryos.modules.orders.models import Order
from factoryos.modules.production.models import TimeBooking
from factoryos.modules.production.services.booking_service import (
    FINISHED_ORDER_STATUSES,
    get_manual_start_data,
    start_production,
    end_booking,
    resume_booking
)

from . import bp


def _render_manual_start(selected_order_id=None, selected_machine_id=None, comment=""):
    data = get_manual_start_data()
    return render_template(
        "production/booking/manual_start.html",
        **data,
        selected_order_id=selected_order_id,
        selected_machine_id=selected_machine_id,
        comment=comment,
    )


def _handle_start_request():
    order_id = request.form.get("order_id", type=int)
    machine_id = request.form.get("machine_id", type=int)
    comment = request.form.get("comment", "")

    if not order_id or not machine_id:
        flash("Bitte Auftrag und Maschine auswählen.", "danger")
        return _render_manual_start(order_id, machine_id, comment)

    order = Order.query.get(order_id)
    machine = Machine.query.get(machine_id)

    if not order:
        flash("Der ausgewählte Auftrag wurde nicht gefunden.", "danger")
        return _render_manual_start(None, machine_id, comment)

    if not machine or machine.machine_status != "aktiv":
        flash("Die ausgewählte Maschine ist nicht aktiv oder wurde nicht gefunden.", "danger")
        return _render_manual_start(order_id, None, comment)

    if (order.status or "").lower() in FINISHED_ORDER_STATUSES:
        flash("Fertige oder gesperrte Aufträge können nicht gestartet werden.", "danger")
        return _render_manual_start(None, machine_id, comment)

    active_order_booking = (
        TimeBooking.query
        .filter_by(order_id=order.id)
        .filter(TimeBooking.end_time.is_(None))
        .order_by(TimeBooking.start_time.desc())
        .first()
    )

    if active_order_booking:
        if active_order_booking.machine_id == machine.id:
            flash(
                f"Auftrag {order.order_no} läuft bereits auf Maschine {machine.machine_no}.",
                "warning",
            )
        else:
            running_machine = active_order_booking.machine
            machine_label = running_machine.machine_no if running_machine else "einer anderen Maschine"
            flash(
                f"Auftrag {order.order_no} läuft bereits auf {machine_label}. "
                "Bitte diese Buchung zuerst beenden.",
                "danger",
            )
        return _render_manual_start(order_id, machine_id, comment)

    active_machine_booking = (
        TimeBooking.query
        .filter_by(machine_id=machine.id)
        .filter(TimeBooking.end_time.is_(None))
        .order_by(TimeBooking.start_time.desc())
        .first()
    )

    machine_is_occupied = (
        active_machine_booking is not None
        and active_machine_booking.process != "FREI"
    )
    if machine_is_occupied and request.form.get("replace_active") != "yes":
        active_label = (
            active_machine_booking.order.order_no
            if active_machine_booking.order
            else active_machine_booking.process
        )
        flash(
            f"Maschine {machine.machine_no} ist durch {active_label} belegt. "
            "Bitte das Ablösen der laufenden Buchung bestätigen.",
            "warning",
        )
        return _render_manual_start(order_id, machine_id, comment)

    start_production(
        user_id=current_user.id,
        order_id=order.id,
        machine_id=machine.id,
        comment=comment,
    )

    flash(
        f"Auftrag {order.order_no} wurde auf Maschine {machine.machine_no} gestartet.",
        "success",
    )
    return redirect(url_for("production.booking_dashboard"))


@bp.route("/booking/start", methods=["GET", "POST"])
@login_required
def manual_start():
    if request.method == "POST":
        return _handle_start_request()

    return _render_manual_start(
        selected_order_id=request.args.get("order_id", type=int),
        selected_machine_id=request.args.get("machine_id", type=int),
    )


@bp.route("/start", methods=["POST"])
@login_required
def start_booking():
    """Kompatibilitätsroute für bestehende Start-Formulare."""
    return _handle_start_request()


@bp.route("/end/<int:booking_id>", methods=["POST"])
@login_required
def end_booking_route(booking_id):

    action = request.form.get("action")

    end_booking(
        booking_id,
        user_id=current_user.id,
        action=action
    )

    return redirect(url_for("production.booking_dashboard"))


@bp.route("/resume/<int:booking_id>", methods=["POST"])
@login_required
def resume_from_pause_or_downtime(booking_id):

    resume_booking(
        booking_id,
        user_id=current_user.id
    )

    return redirect(url_for("production.booking_dashboard"))
