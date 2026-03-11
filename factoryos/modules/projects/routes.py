@app.route("/projects")
@login_required
def projects_dashboard():
    q = request.args.get("q", "").strip()
    only_mine = request.args.get("only_mine", "0") == "1"

    base = (
        Order.query
        .filter_by(is_project=True)
        .filter(Order.status != "fertig")
        .filter(Order.status != "gesperrt")
    )

    # Nur meine Projekte (Projektleiter = current_user)
    if only_mine:
        base = base.filter(Order.project_leader_id == current_user.id)

    # Suchfilter
    if q:
        like = f"%{q}%"
        base = base.outerjoin(User, Order.project_leader_id == User.id).filter(
            db.or_(
                Order.order_no.ilike(like),
                Order.tool_no.ilike(like),
                Order.article.ilike(like),
                Order.description.ilike(like),
                User.username.ilike(like)
            )
        )

    projects = base.order_by(Order.tool_no.asc(), Order.order_no.asc()).all()
    project_count = len(projects)

    # Eigene laufende Projektzeiten
    active = (
        TimeBooking.query
        .filter_by(user_id=current_user.id)
        .filter(TimeBooking.end_time.is_(None))
        .filter(TimeBooking.process == "PROJEKT")
        .order_by(TimeBooking.start_time.desc())
        .all()
    )

    # Eigene Historie
    history = (
        TimeBooking.query
        .filter_by(user_id=current_user.id)
        .filter(TimeBooking.process == "PROJEKT")
        .filter(TimeBooking.end_time.isnot(None))
        .order_by(TimeBooking.start_time.desc())
        .limit(50)
        .all()
    )

    return render_template(
        "projects_dashboard.html",
        projects=projects,
        active=active,
        history=history,
        q=q,
        only_mine=only_mine,
        project_count=project_count
    )


@app.route("/projects/start/<int:order_id>", methods=["POST"])
@login_required
def projects_start(order_id):
    order = Order.query.get_or_404(order_id)

    if not order.is_project:
        flash("Dieser Auftrag ist kein Projekt.", "danger")
        return redirect(url_for("projects_dashboard"))

    # Hinweis wenn bereits Projekte laufen
    running = (
        TimeBooking.query
        .filter_by(user_id=current_user.id)
        .filter(TimeBooking.end_time.is_(None))
        .filter(TimeBooking.process == "PROJEKT")
        .count()
    )

    if running > 0:
        flash("Hinweis: Du hast bereits ein anderes Projekt aktiv laufen.", "warning")

    b = TimeBooking(
        user_id=current_user.id,
        order_id=order.id,
        machine_id=None,
        type="START",
        process="PROJEKT",
        tool_no=order.tool_no,
        start_time=datetime.utcnow()
    )
    db.session.add(b)
    db.session.commit()

    flash("Projekt gestartet.", "success")
    return redirect(url_for("projects_dashboard"))

@app.route("/projects/close/<int:order_id>", methods=["POST"])
@login_required
def projects_close(order_id):
    order = Order.query.get_or_404(order_id)

    if not order.is_project:
        flash("Dies ist kein Projekt.", "danger")
        return redirect(url_for("projects_dashboard"))

    # Nur Admin/Schichtleiter (oder Admin)
    if current_user.role not in ["admin", "schichtleiter"]:
        flash("Keine Berechtigung.", "danger")
        return redirect(url_for("projects_dashboard"))

    # Laufende Projekt-Buchungen zu diesem Projekt beenden
    running = (
        TimeBooking.query
        .filter_by(order_id=order.id)
        .filter(TimeBooking.process == "PROJEKT")
        .filter(TimeBooking.end_time.is_(None))
        .all()
    )

    for b in running:
        b.end_time = datetime.utcnow()

    order.status = "fertig"
    db.session.commit()

    flash("Projekt geschlossen.", "success")
    return redirect(url_for("projects_dashboard"))



@app.route("/projects/stop/<int:booking_id>", methods=["GET", "POST"])
@login_required
def projects_stop(booking_id):
    b = TimeBooking.query.get_or_404(booking_id)

    if b.user_id != current_user.id:
        flash("Keine Berechtigung.", "danger")
        return redirect(url_for("projects_dashboard"))

    if b.end_time is not None:
        flash("Dieser Eintrag ist bereits beendet.", "warning")
        return redirect(url_for("projects_dashboard"))

    if b.process != "PROJEKT":
        flash("Dies ist keine Projektbuchung.", "warning")
        return redirect(url_for("projects_dashboard"))

    if request.method == "POST":
        comment = request.form.get("comment", "").strip()
        b.comment = comment if comment else None
        b.end_time = datetime.utcnow()
        db.session.commit()

        flash("Projektzeit beendet.", "success")
        return redirect(url_for("projects_dashboard"))

    return render_template("projects_stop.html", b=b)
