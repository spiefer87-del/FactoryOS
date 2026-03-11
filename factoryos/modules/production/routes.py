from datetime import datetime

from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    request,
    flash
)

from flask_login import login_required, current_user
from sqlalchemy import func

from extensions import db

from factoryos.models.machine import Machine

from factoryos.modules.production.models import (
    TimeBooking,
    Order,
    QuantityReport,
    DowntimeReason
)

from factoryos.modules.production.services import (
    close_all_active_bookings,
    start_machine_free,
    get_active_machine_state
)

production_bp = Blueprint(
    "production",
    __name__,
    url_prefix="/production"
)


# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------

@production_bp.route("/dashboard")
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

    qty_sums = (
        db.session.query(
            QuantityReport.order_id,
            func.coalesce(func.sum(QuantityReport.good_qty), 0).label("good_sum"),
            func.coalesce(func.sum(QuantityReport.scrap_qty), 0).label("scrap_sum"),
        )
        .group_by(QuantityReport.order_id)
        .all()
    )

    qty_by_order = {
        row.order_id: {
            "good": row.good_sum,
            "scrap": row.scrap_sum
        }
        for row in qty_sums
    }

    return render_template(
        "dashboard_machines.html",
        machines=machines,
        active_by_machine=active_by_machine,
        qty_by_order=qty_by_order,
        reasons=reasons
    )


# --------------------------------------------------
# START BOOKING
# --------------------------------------------------

@production_bp.route("/start", methods=["GET", "POST"])
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


# --------------------------------------------------
# SETUP / RUEST
# --------------------------------------------------

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

@app.route("/orders/<order_no>")
@login_required
def order_detail(order_no):
    # Auftrag holen
    o = Order.query.filter_by(order_no=order_no).first_or_404()

    # ToolMasterdata holen (über tool_no)
    tool = None
    if o.tool_no:
        tool = ToolMasterdata.query.filter_by(tool_no=o.tool_no).first()

    # Ist-Menge / Ausschuss summieren
    sums = (
        db.session.query(
            func.coalesce(func.sum(QuantityReport.good_qty), 0).label("good_sum"),
            func.coalesce(func.sum(QuantityReport.scrap_qty), 0).label("scrap_sum"),
        )
        .filter(QuantityReport.order_id == o.id)
        .first()
    )

    good = int(sums.good_sum or 0)
    scrap = int(sums.scrap_sum or 0)

    target = int(o.target_qty or 0)
    rest = target - good
    if rest < 0:
        rest = 0

    # ----------------------------
    # Berechnungen aus Stammdaten
    # ----------------------------
    shot_weight_g = None
    cycle_time_s = None

    material_need_kg = None
    kg_per_hour = None
    parts_per_hour = None

    if tool:
        # ACHTUNG: Feldnamen müssen zu deinem Model passen!
        # (ich gehe von shot_weight_g und cycle_time_s aus)
        shot_weight_g = tool.shot_weight_g
        cycle_time_s = tool.cycle_time_s

        if shot_weight_g and target > 0:
            material_need_kg = (target * float(shot_weight_g)) / 1000.0

        if shot_weight_g and cycle_time_s and cycle_time_s > 0:
            parts_per_hour = 3600.0 / float(cycle_time_s)
            kg_per_hour = (parts_per_hour * float(shot_weight_g)) / 1000.0

    return render_template(
        "order_detail.html",
        o=o,
        tool=tool,
        good=good,
        scrap=scrap,
        rest=rest,
        material_need_kg=material_need_kg,
        kg_per_hour=kg_per_hour,
        parts_per_hour=parts_per_hour
    )