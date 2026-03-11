@app.route("/report/times")
@login_required
def report_times():

    order_q = request.args.get("order", "").strip()
    tool_q = request.args.get("tool", "").strip()
    article_q = request.args.get("article", "").strip()
    user_q = request.args.get("user", "").strip()
    machine_q = request.args.get("machine", "").strip()

    q = (
        TimeBooking.query
        .join(User, TimeBooking.user_id == User.id)
        .outerjoin(Order, TimeBooking.order_id == Order.id)
        .outerjoin(Machine, TimeBooking.machine_id == Machine.id)
    )

    if order_q:
        q = q.filter(Order.order_no.contains(order_q))

    if tool_q:
        q = q.filter(TimeBooking.tool_no.contains(tool_q))

    if article_q:
        q = q.filter(Order.article.contains(article_q))

    if user_q:
        q = q.filter(User.username.contains(user_q))

    if machine_q:
        q = q.filter(Machine.name.contains(machine_q))

    bookings = q.order_by(TimeBooking.start_time.desc()).limit(1000).all()

    totals = {
        "PROD": 0,
        "RUEST": 0,
        "ABRUEST": 0,
        "STOERUNG": 0,
        "WARTUNG": 0,
        "REPARATUR": 0,
        "SCHULUNG": 0,
        "PAUSE": 0,
        "FREI": 0
    }

    now = datetime.utcnow()

    for b in bookings:

        end_time = b.end_time if b.end_time else now

        seconds = int((end_time - b.start_time).total_seconds())

        key = b.process if b.process else b.type

        if key in totals:
            totals[key] += seconds

    return render_template(
        "report_times.html",
        bookings=bookings,
        totals=totals,
        order_q=order_q,
        tool_q=tool_q,
        article_q=article_q,
        user_q=user_q,
        machine_q=machine_q,
        now=now
    )


@app.route("/report/times/export")
@login_required
def report_times_export():
    if current_user.role not in ["admin", "schichtleiter"]:
        flash("Keine Berechtigung.", "danger")
        return redirect(url_for("dashboard"))

    # Filter (gleich wie report_times)
    order_q = request.args.get("order", "").strip()
    tool_q = request.args.get("tool", "").strip()
    article_q = request.args.get("article", "").strip()
    user_q = request.args.get("user", "").strip()
    machine_q = request.args.get("machine", "").strip()

    q = TimeBooking.query
    q = q.join(User, TimeBooking.user_id == User.id)
    q = q.outerjoin(Order, TimeBooking.order_id == Order.id)
    q = q.outerjoin(Machine, TimeBooking.machine_id == Machine.id)
    q = q.outerjoin(DowntimeReason, TimeBooking.downtime_reason_id == DowntimeReason.id)

    q = q.filter(TimeBooking.end_time.isnot(None))

    if order_q:
        q = q.filter(Order.order_no.contains(order_q))

    if tool_q:
        q = q.filter(TimeBooking.tool_no.contains(tool_q))

    if article_q:
        q = q.filter(Order.article.contains(article_q))

    if user_q:
        q = q.filter(User.username.contains(user_q))

    if machine_q:
        q = q.filter(Machine.name.contains(machine_q))

    bookings = q.order_by(TimeBooking.start_time.asc()).all()

    # Excel bauen
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Zeiten"

    headers = [
        "Start",
        "Ende",
        "Dauer (hh:mm:ss)",
        "Prozess",
        "Auftrag",
        "Artikel",
        "Werkzeug",
        "Maschine",
        "Mitarbeiter",
        "Störgrund",
        "Kommentar"
    ]
    ws.append(headers)

    for b in bookings:
        sec = int((b.end_time - b.start_time).total_seconds())
        h = sec // 3600
        m = (sec % 3600) // 60
        s = sec % 60
        duration_str = f"{h:02d}:{m:02d}:{s:02d}"

        ws.append([
            b.start_time.strftime("%d.%m.%Y %H:%M:%S") if b.start_time else "",
            b.end_time.strftime("%d.%m.%Y %H:%M:%S") if b.end_time else "",
            duration_str,
            b.process or b.type or "",
            b.order.order_no if b.order else "",
            b.order.article if b.order and b.order.article else "",
            b.tool_no or "",
            b.machine.name if b.machine else "",
            b.user.username if b.user else "",
            b.downtime_reason.name if b.downtime_reason else "",
            b.comment or ""
        ])

    # Spaltenbreite automatisch
    for col in range(1, len(headers) + 1):
        ws.column_dimensions[get_column_letter(col)].width = 20

    # Datei in Memory
    file_data = BytesIO()
    wb.save(file_data)
    file_data.seek(0)

    return send_file(
        file_data,
        as_attachment=True,
        download_name="zeitauswertung.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@app.route("/report/orders")
@login_required
@role_required("admin", "schichtleiter")
def report_orders():
    # Ist = Summe Gutteile, Ausschuss = Summe Ausschuss
    rows = (
        db.session.query(
            Order.id,
            Order.order_no,
            Order.article,
            Order.target_qty,
            Order.status,
            func.coalesce(func.sum(QuantityReport.good_qty), 0).label("good_sum"),
            func.coalesce(func.sum(QuantityReport.scrap_qty), 0).label("scrap_sum"),
        )
        .outerjoin(QuantityReport, QuantityReport.order_id == Order.id)
        .group_by(Order.id)
        .order_by(Order.order_no.asc())
        .all()
    )

    # für Template schön vorbereiten
    report = []
    for r in rows:
        target = r.target_qty or 0
        good = r.good_sum or 0
        scrap = r.scrap_sum or 0

        progress = 0
        if target > 0:
            progress = round((good / target) * 100, 1)

        report.append({
            "order_no": r.order_no,
            "article": r.article,
            "target": target,
            "good": good,
            "scrap": scrap,
            "status": r.status,
            "progress": progress
        })

    return render_template("report_orders.html", report=report)