bp = Blueprint(
    "production_booking",
    __name__,
    url_prefix="/production"
)
--------------------------------------------------
# START BOOKING
# --------------------------------------------------

@bp.route("/start", methods=["GET", "POST"])
@login_required
def start_booking():

    orders = (
        Order.query
        .filter_by(is_project=False)
        .filter(Order.status.in_(["offen", "in_arbeit"]))
        .order_by(Order.order_no.asc())
        .all()
    )

    machines = (
        Machine.query
        .filter_by(active=True)
        .order_by(Machine.name.asc())
        .all()
    )

    if request.method == "POST":

        order_id_raw = request.form.get("order_id")
        machine_id_raw = request.form.get("machine_id")

        try:
            order_id = int(order_id_raw)
            machine_id = int(machine_id_raw)
        except:
            flash("Ungültige Auswahl.", "danger")
            return redirect(url_for("production.dashboard"))

        order = Order.query.get_or_404(order_id)
        machine = Machine.query.get_or_404(machine_id)

        close_all_active_bookings(machine_id)

        if order.status == "offen":
            order.status = "in_arbeit"

        new_booking = TimeBooking(
            user_id=current_user.id,
            order_id=order.id,
            machine_id=machine.id,
            type="START",
            process="PROD",
            tool_no=order.tool_no,
            start_time=datetime.utcnow()
        )

        db.session.add(new_booking)
        db.session.commit()

        flash(f"Produktion auf {machine.name} gestartet.", "success")

        return redirect(url_for("production.dashboard"))

    return render_template(
        "start_booking.html",
        orders=orders,
        machines=machines
    )


# --------------------------------------------------
# END / PAUSE / STOP
# --------------------------------------------------

@production_bp.route("/end/<int:booking_id>", methods=["POST"])
@login_required
def end_booking(booking_id):

    booking = TimeBooking.query.get_or_404(booking_id)

    if booking.end_time is not None:
        flash("Bereits beendet.", "warning")
        return redirect(url_for("production.dashboard"))

    action = request.form.get("action")

    booking.end_time = datetime.utcnow()

    machine_id = booking.machine_id

    if action == "PAUSE":

        pause = TimeBooking(
            user_id=current_user.id,
            order_id=booking.order_id,
            machine_id=machine_id,
            type="PAUSE",
            process="PAUSE",
            tool_no=booking.tool_no,
            start_time=datetime.utcnow()
        )

        db.session.add(pause)
        db.session.commit()

        flash("Pause gestartet.", "info")

        return redirect(url_for("production.dashboard"))

    start_machine_free(machine_id, current_user.id)

    db.session.commit()

    flash("Vorgang beendet. Maschine ist frei.", "success")

    return redirect(url_for("production.dashboard"))


# --------------------------------------------------
# RESUME
# --------------------------------------------------

@production_bp.route("/resume/<int:booking_id>", methods=["POST"])
@login_required
def resume_from_pause_or_downtime(booking_id):

    booking = TimeBooking.query.get_or_404(booking_id)

    if booking.end_time is not None:
        flash("Bereits beendet.", "warning")
        return redirect(url_for("production.dashboard"))

    booking.end_time = datetime.utcnow()

    resume_order_id = booking.order_id or booking.prev_order_id

    if not resume_order_id:
        start_machine_free(booking.machine_id, current_user.id)
        db.session.commit()

        flash("Beendet. Maschine ist frei.", "success")

        return redirect(url_for("production.dashboard"))

    order = Order.query.get(resume_order_id)

    if not order or order.status == "gesperrt":
        start_machine_free(booking.machine_id, current_user.id)
        db.session.commit()

        flash("Beendet. Maschine ist frei.", "warning")

        return redirect(url_for("production.dashboard"))

    new_start = TimeBooking(
        user_id=current_user.id,
        order_id=order.id,
        machine_id=booking.machine_id,
        type="START",
        process="PROD",
        tool_no=order.tool_no,
        start_time=datetime.utcnow()
    )

    db.session.add(new_start)
    db.session.commit()

    flash("Produktion fortgesetzt.", "success")

    return redirect(url_for("production.dashboard"))

