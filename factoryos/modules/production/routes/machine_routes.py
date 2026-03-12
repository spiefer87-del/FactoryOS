bp = Blueprint(
    "production_machine",
    __name__,
    url_prefix="/production"
)

@production_bp.route("/machine/<int:machine_id>/setup", methods=["GET", "POST"])
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

        mode = request.form.get("mode")
        order_id_raw = request.form.get("order_id", "").strip()
        tool_no = request.form.get("tool_no", "").strip()
        comment = request.form.get("comment", "").strip()

        if mode not in ["RUEST", "ABRUEST"]:
            flash("Ungültiger Modus.", "danger")
            return redirect(url_for("production.dashboard"))

        selected_order = None

        if order_id_raw:
            try:
                selected_order = Order.query.get(int(order_id_raw))
            except:
                selected_order = None

        if selected_order and selected_order.tool_no:
            tool_no = selected_order.tool_no

        if not tool_no:
            flash("Bitte Werkzeug-Nr. eingeben oder Auftrag auswählen.", "danger")
            return redirect(url_for("production.machine_setup", machine_id=machine_id))

        close_all_active_bookings(machine_id)

        b = TimeBooking(
            user_id=current_user.id,
            order_id=selected_order.id if selected_order else None,
            machine_id=machine_id,
            type="START",
            process=mode,
            tool_no=tool_no,
            comment=comment or None,
            start_time=datetime.utcnow()
        )

        db.session.add(b)
        db.session.commit()

        flash(f"{mode} gestartet.", "success")

        return redirect(url_for("production.dashboard"))

    return render_template(
        "machine_setup.html",
        machine=machine,
        orders=orders
    )


# --------------------------------------------------
# MACHINE EVENT
# --------------------------------------------------

@production_bp.route("/machine/<int:machine_id>/event", methods=["GET", "POST"])
@login_required
def machine_event(machine_id):

    machine = Machine.query.get_or_404(machine_id)

    if request.method == "POST":

        event = request.form.get("event")
        comment = request.form.get("comment", "").strip()

        allowed = ["STOERUNG", "WARTUNG", "REPARATUR", "SCHULUNG"]

        if event not in allowed:
            flash("Ungültiger Status.", "danger")
            return redirect(url_for("production.dashboard"))

        close_all_active_bookings(machine_id)

        b = TimeBooking(
            user_id=current_user.id,
            order_id=None,
            machine_id=machine_id,
            type="START",
            process=event,
            tool_no=None,
            comment=comment or None,
            start_time=datetime.utcnow()
        )

        db.session.add(b)
        db.session.commit()

        flash(f"{event} gestartet.", "success")

        return redirect(url_for("production.dashboard"))

    return render_template(
        "machine_event.html",
        machine=machine
    )


# --------------------------------------------------
# DOWNTIME
# --------------------------------------------------

@production_bp.route("/machine/<int:machine_id>/downtime", methods=["GET", "POST"])
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

        reason_id = request.form.get("reason_id")
        comment = request.form.get("comment", "").strip()

        state = get_active_machine_state(machine_id)

        prev_order_id = None
        prev_tool_no = None

        if state["booking"]:
            prev_order_id = state["booking"].order_id
            prev_tool_no = state["booking"].tool_no

        close_all_active_bookings(machine_id)

        b = TimeBooking(
            user_id=current_user.id,
            order_id=None,
            prev_order_id=prev_order_id,
            machine_id=machine_id,
            type="START",
            process="STOERUNG",
            tool_no=prev_tool_no,
            downtime_reason_id=int(reason_id) if reason_id else None,
            comment=comment or None,
            start_time=datetime.utcnow()
        )

        db.session.add(b)
        db.session.commit()

        flash("Störung gestartet.", "warning")

        return redirect(url_for("production.dashboard"))

    return render_template(
        "machine_downtime.html",
        machine=machine,
        reasons=reasons
    )
