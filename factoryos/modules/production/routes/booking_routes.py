from flask import Blueprint, redirect, url_for, request, flash
from flask_login import login_required, current_user

from factoryos.modules.production.services.booking_service import (
    start_production,
    end_booking,
    resume_booking
)

from . import bp


@bp.route("/start", methods=["POST"])
@login_required
def start_booking():

    order_id = request.form.get("order_id")
    machine_id = request.form.get("machine_id")

    start_production(
        user_id=current_user.id,
        order_id=order_id,
        machine_id=machine_id
    )

    flash("Produktion gestartet.", "success")

    return redirect(url_for("production_dashboard.dashboard"))


@bp.route("/end/<int:booking_id>", methods=["POST"])
@login_required
def end_booking_route(booking_id):

    action = request.form.get("action")

    end_booking(
        booking_id,
        user_id=current_user.id,
        action=action
    )

    return redirect(url_for("production_dashboard.dashboard"))


@bp.route("/resume/<int:booking_id>", methods=["POST"])
@login_required
def resume_from_pause_or_downtime(booking_id):

    resume_booking(
        booking_id,
        user_id=current_user.id
    )

    return redirect(url_for("production_dashboard.dashboard"))
