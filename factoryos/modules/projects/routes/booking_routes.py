from datetime import datetime
from flask import Blueprint, redirect, url_for, flash, render_template, request
from flask_login import login_required, current_user

from factoryos.extensions import db
from factoryos.modules.production.models import TimeBooking
from factoryos.modules.orders.models import Order

from . import bp


@bp.route("/start/<int:order_id>", methods=["POST"])
@login_required
def projects_start(order_id):

    order = Order.query.get_or_404(order_id)

    if not order.is_project:
        flash("Dieser Auftrag ist kein Projekt.", "danger")
        return redirect(url_for("projects.projects_home"))

    existing = (
        TimeBooking.query
        .filter_by(
            user_id=current_user.id,
            order_id=order.id,
            process="PROJEKT"
        )
        .filter(TimeBooking.end_time.is_(None))
        .first()
    )

    if existing:
        flash("Projekt läuft bereits.", "warning")
        return redirect(url_for("projects.projects_home"))

    b = TimeBooking(
        user_id=current_user.id,
        order_id=order.id,
        process="PROJEKT",
        type="START",
        tool_no=order.tool_no,
        start_time=datetime.utcnow()
    )

    db.session.add(b)
    db.session.commit()

    flash("Projekt gestartet.", "success")
    return redirect(url_for("projects.projects_home"))


@bp.route("/stop/<int:booking_id>", methods=["GET", "POST"])
@login_required
def projects_stop(booking_id):

    b = TimeBooking.query.get_or_404(booking_id)

    if b.user_id != current_user.id:
        flash("Keine Berechtigung.", "danger")
        return redirect(url_for("projects.projects_home"))

    if request.method == "POST":
        comment = request.form.get("comment", "").strip()

        b.comment = comment if comment else None
        b.end_time = datetime.utcnow()

        db.session.commit()

        flash("Projektzeit beendet.", "success")
        return redirect(url_for("projects.projects_home"))

    return render_template("projects_stop.html", b=b)
