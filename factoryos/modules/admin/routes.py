
@app.route("/admin/reasons")
@login_required
@role_required("admin", "schichtleiter")
def admin_reasons():
    reasons = DowntimeReason.query.order_by(DowntimeReason.name.asc()).all()
    return render_template("admin_reasons.html", reasons=reasons)


@app.route("/admin/reasons/create", methods=["GET", "POST"])
@login_required
@role_required("admin")
def admin_reasons_create():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        active = True if request.form.get("active") == "on" else False

        if not name:
            flash("Bitte Namen angeben.", "danger")
            return redirect(url_for("admin_reasons_create"))

        if DowntimeReason.query.filter_by(name=name).first():
            flash("Störgrund existiert bereits.", "danger")
            return redirect(url_for("admin_reasons_create"))

        r = DowntimeReason(name=name, active=active)
        db.session.add(r)
        db.session.commit()

        flash("Störgrund angelegt.", "success")
        return redirect(url_for("admin_reasons"))

    return render_template("admin_reasons_create.html")

@app.route("/admin/reasons/edit/<int:reason_id>", methods=["GET", "POST"])
@login_required
@role_required("admin")
def admin_reasons_edit(reason_id):
    r = DowntimeReason.query.get_or_404(reason_id)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        active = True if request.form.get("active") == "on" else False

        if not name:
            flash("Bitte Namen angeben.", "danger")
            return redirect(url_for("admin_reasons_edit", reason_id=reason_id))

        existing = DowntimeReason.query.filter(DowntimeReason.name == name, DowntimeReason.id != r.id).first()
        if existing:
            flash("Störgrund existiert bereits.", "danger")
            return redirect(url_for("admin_reasons_edit", reason_id=reason_id))

        r.name = name
        r.active = active

        db.session.commit()
        flash("Störgrund gespeichert.", "success")
        return redirect(url_for("admin_reasons"))

    return render_template("admin_reasons_edit.html", reason=r)

@app.route("/admin/reasons/toggle/<int:reason_id>", methods=["POST"])
@login_required
@role_required("admin")
def admin_reasons_toggle(reason_id):
    r = DowntimeReason.query.get_or_404(reason_id)
    r.active = not r.active
    db.session.commit()

    flash("Störgrundstatus geändert.", "success")
    return redirect(url_for("admin_reasons"))

@app.route("/admin")
@login_required
@role_required("admin", "schichtleiter")
def admin_home():
    return render_template("admin_home.html")


@app.route("/admin/users")
@login_required
@role_required("admin")
def admin_users():
    users = User.query.order_by(User.username.asc()).all()
    return render_template("admin_users.html", users=users)


@app.route("/admin/users/create", methods=["GET", "POST"])
@login_required
@role_required("admin")
def admin_users_create():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        role = request.form.get("role", "mitarbeiter")
        active = True if request.form.get("active") == "on" else False

        if not username or not password:
            flash("Bitte Benutzername und Passwort angeben.", "danger")
            return redirect(url_for("admin_users_create"))

        if User.query.filter_by(username=username).first():
            flash("Benutzername existiert bereits.", "danger")
            return redirect(url_for("admin_users_create"))

        u = User(username=username, role=role, active=active)
        u.set_password(password)

        db.session.add(u)
        db.session.commit()

        flash("Benutzer angelegt.", "success")
        return redirect(url_for("admin_users"))

    return render_template("admin_users_create.html")

@app.route("/admin/users/edit/<int:user_id>", methods=["GET", "POST"])
@login_required
@role_required("admin")
def admin_users_edit(user_id):
    u = User.query.get_or_404(user_id)

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        role = request.form.get("role", "mitarbeiter")
        active = True if request.form.get("active") == "on" else False
        new_password = request.form.get("new_password", "").strip()

        if not username:
            flash("Bitte Benutzername angeben.", "danger")
            return redirect(url_for("admin_users_edit", user_id=user_id))

        # Username unique check
        existing = User.query.filter(User.username == username, User.id != u.id).first()
        if existing:
            flash("Benutzername existiert bereits.", "danger")
            return redirect(url_for("admin_users_edit", user_id=user_id))

        # Admin darf sich nicht selbst deaktivieren
        if u.id == current_user.id and active is False:
            flash("Du kannst dich nicht selbst deaktivieren.", "warning")
            return redirect(url_for("admin_users_edit", user_id=user_id))

        u.username = username
        u.role = role
        u.active = active

        # Passwort optional ändern
        if new_password:
            u.set_password(new_password)

        db.session.commit()
        flash("Benutzer gespeichert.", "success")
        return redirect(url_for("admin_users"))

    return render_template("admin_users_edit.html", user=u)



@app.route("/admin/users/toggle/<int:user_id>", methods=["POST"])
@login_required
@role_required("admin")
def admin_users_toggle(user_id):
    if current_user.id == user_id:
        flash("Du kannst dich nicht selbst deaktivieren.", "warning")
        return redirect(url_for("admin_users"))

    u = User.query.get_or_404(user_id)
    u.active = not u.active
    db.session.commit()

    flash("Benutzerstatus geändert.", "success")
    return redirect(url_for("admin_users"))


@app.route("/admin/machines")
@login_required
@role_required("admin", "schichtleiter")
def admin_machines():
    machines = Machine.query.order_by(Machine.name.asc()).all()
    return render_template("admin_machines.html", machines=machines)


@app.route("/admin/machines/create", methods=["GET", "POST"])
@login_required
@role_required("admin")
def admin_machines_create():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        location = request.form.get("location", "").strip()
        active = True if request.form.get("active") == "on" else False

        if not name:
            flash("Bitte Maschinenname angeben.", "danger")
            return redirect(url_for("admin_machines_create"))

        if Machine.query.filter_by(name=name).first():
            flash("Maschine existiert bereits.", "danger")
            return redirect(url_for("admin_machines_create"))

        m = Machine(name=name, location=location if location else None, active=active)
        db.session.add(m)
        db.session.commit()

        flash("Maschine angelegt.", "success")
        return redirect(url_for("admin_machines"))

    return render_template("admin_machines_create.html")

@app.route("/admin/machines/edit/<int:machine_id>", methods=["GET", "POST"])
@login_required
@role_required("admin")
def admin_machines_edit(machine_id):
    m = Machine.query.get_or_404(machine_id)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        location = request.form.get("location", "").strip()
        active = True if request.form.get("active") == "on" else False

        if not name:
            flash("Bitte Maschinenname angeben.", "danger")
            return redirect(url_for("admin_machines_edit", machine_id=machine_id))

        # Check: Name muss unique sein
        existing = Machine.query.filter(Machine.name == name, Machine.id != m.id).first()
        if existing:
            flash("Maschinenname existiert bereits.", "danger")
            return redirect(url_for("admin_machines_edit", machine_id=machine_id))

        m.name = name
        m.location = location if location else None
        m.active = active

        db.session.commit()
        flash("Maschine gespeichert.", "success")
        return redirect(url_for("admin_machines"))

    return render_template("admin_machines_edit.html", machine=m)


@app.route("/admin/machines/toggle/<int:machine_id>", methods=["POST"])
@login_required
@role_required("admin")
def admin_machines_toggle(machine_id):
    m = Machine.query.get_or_404(machine_id)
    m.active = not m.active
    db.session.commit()

    flash("Maschinenstatus geändert.", "success")
    return redirect(url_for("admin_machines"))


@app.route("/admin/orders")
@login_required
@role_required("admin", "schichtleiter")
def admin_orders():

    q = request.args.get("q", "").strip()

    # Wichtig: None erkennen, nicht "" !
    status_filter = request.args.get("status", None)

    # Wenn status nicht gesetzt wurde -> default "offen"
    if status_filter is None:
        status_filter = "offen"

    # Wenn User "(alle)" gewählt hat -> kommt status=""
    if status_filter == "":
        status_filter = ""

    # Query
    query = (
        db.session.query(
            Order,
            func.coalesce(func.sum(QuantityReport.good_qty), 0).label("good_sum")
        )
        .outerjoin(QuantityReport, QuantityReport.order_id == Order.id)
        .group_by(Order.id)
    )

    # Suche
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Order.order_no.ilike(like),
                Order.article.ilike(like),
                Order.description.ilike(like),
                Order.tool_no.ilike(like),
            )
        )

    # Status Filter
    if status_filter in ["offen", "in_arbeit", "fertig", "gesperrt"]:
        query = query.filter(Order.status == status_filter)

    # Wenn status_filter == "" => (alle) => kein Filter!

    query = query.order_by(Order.order_no.asc())
    rows = query.all()

    orders = []
    for order, good_sum in rows:
        target = order.target_qty or 0
        good = good_sum or 0
        rest = target - good
        if rest < 0:
            rest = 0

        orders.append({
            "order": order,
            "good": int(good),
            "rest": int(rest)
        })

    order_count = len(orders)

    return render_template(
        "admin_orders.html",
        orders=orders,
        q=q,
        status_filter=status_filter,
        order_count=order_count
    )



@app.route("/admin/orders/create", methods=["GET"])
@login_required
@role_required("admin", "schichtleiter")
def admin_orders_create():
    return render_template("admin_orders_create_choose.html")

@app.route("/admin/orders/create/project", methods=["GET", "POST"])
@login_required
@role_required("admin", "schichtleiter")
def admin_orders_create_project():
    users = User.query.order_by(User.username.asc()).all()
    tools = ToolMasterdata.query.order_by(ToolMasterdata.tool_no.asc()).all()

    if request.method == "POST":
        order_no = request.form.get("order_no", "").strip()

        tool_no = request.form.get("tool_no", "").strip()

        article = request.form.get("article", "").strip()  # Artikelnummer
        article_name = request.form.get("article_name", "").strip()
        location = request.form.get("location", "").strip()

        reason = request.form.get("reason", "").strip()
        description = request.form.get("description", "").strip()
        project_leader_id = request.form.get("project_leader_id", "").strip()

        # Werkzeug Pflicht
        if not tool_no:
            flash("Werkzeug-Nr. ist Pflicht für Projekte.", "danger")
            return redirect(url_for("admin_orders_create_project"))

        # order_no optional -> generieren
        if not order_no:
            order_no = f"PROJ-{tool_no}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"

        if Order.query.filter_by(order_no=order_no).first():
            flash("Projekt existiert bereits.", "danger")
            return redirect(url_for("admin_orders_create_project"))

        # Projektleiter optional
        leader_id_int = None
        if project_leader_id:
            try:
                leader_id_int = int(project_leader_id)
            except:
                leader_id_int = None

        # Beschreibung kombinieren
        final_description = reason
        if description:
            final_description = f"{reason} - {description}"

        o = Order(
            order_no=order_no,
            article=article if article else None,
            article_name=article_name if article_name else None,
            location=location if location else None,
            tool_no=tool_no,
            description=final_description if final_description else None,
            target_qty=0,
            status="offen",
            is_project=True,
            project_leader_id=leader_id_int
        )
        db.session.add(o)
        db.session.commit()

        flash("Projekt angelegt.", "success")
        return redirect(url_for("projects_dashboard"))

    return render_template(
        "admin_orders_create_project.html",
        users=users,
        tools=tools
    )


@app.route("/admin/orders/create/prod", methods=["GET", "POST"])
@login_required
@role_required("admin")
def admin_orders_create_prod():
    tools = ToolMasterdata.query.order_by(ToolMasterdata.tool_no.asc()).all()

    if request.method == "POST":
        order_no = request.form.get("order_no", "").strip()

        article = request.form.get("article", "").strip()  # Artikelnummer
        article_name = request.form.get("article_name", "").strip()
        location = request.form.get("location", "").strip()

        tool_no = request.form.get("tool_no", "").strip()
        description = request.form.get("description", "").strip()
        target_qty = request.form.get("target_qty", "0").strip()
        status = request.form.get("status", "offen")

        if not order_no:
            flash("Bitte Auftragsnummer angeben.", "danger")
            return redirect(url_for("admin_orders_create_prod"))

        if Order.query.filter_by(order_no=order_no).first():
            flash("Auftrag existiert bereits.", "danger")
            return redirect(url_for("admin_orders_create_prod"))

        try:
            target_qty_int = int(target_qty)
        except:
            target_qty_int = 0

        if target_qty_int <= 0:
            flash("Sollmenge muss größer 0 sein.", "danger")
            return redirect(url_for("admin_orders_create_prod"))

        o = Order(
            order_no=order_no,
            article=article if article else None,
            article_name=article_name if article_name else None,
            location=location if location else None,
            tool_no=tool_no if tool_no else None,
            description=description if description else None,
            target_qty=target_qty_int,
            status=status,
            is_project=False
        )
        db.session.add(o)
        db.session.commit()

        flash("Fertigungsauftrag angelegt.", "success")
        return redirect(url_for("admin_orders"))

    return render_template("admin_orders_create_prod.html", tools=tools)


@app.route("/admin/orders/edit/<int:order_id>", methods=["GET", "POST"])
@login_required
@role_required("admin")
def admin_orders_edit(order_id):
    o = Order.query.get_or_404(order_id)

    if request.method == "POST":
        order_no = request.form.get("order_no", "").strip()
        article = request.form.get("article", "").strip()
        tool_no = request.form.get("tool_no", "").strip()
        description = request.form.get("description", "").strip()
        target_qty = request.form.get("target_qty", "0").strip()
        status = request.form.get("status", "offen")

        if not order_no:
            flash("Bitte Auftragsnummer angeben.", "danger")
            return redirect(url_for("admin_orders_edit", order_id=order_id))

        existing = Order.query.filter(Order.order_no == order_no, Order.id != o.id).first()
        if existing:
            flash("Auftragsnummer existiert bereits.", "danger")
            return redirect(url_for("admin_orders_edit", order_id=order_id))

        try:
            target_qty_int = int(target_qty)
        except:
            target_qty_int = 0

        o.order_no = order_no
        o.article = article if article else None
        o.tool_no = tool_no if tool_no else None
        o.description = description if description else None
        o.target_qty = target_qty_int
        o.status = status

        db.session.commit()
        flash("Auftrag gespeichert.", "success")
        return redirect(url_for("admin_orders"))

    return render_template("admin_orders_edit.html", order=o)

@app.route("/admin/orders/delete/<int:order_id>", methods=["POST"])
@login_required
@role_required("admin")
def admin_orders_delete(order_id):
    o = Order.query.get_or_404(order_id)

    # Prüfen ob Auftrag aktiv läuft
    running = (
        TimeBooking.query
        .filter_by(order_id=o.id)
        .filter(TimeBooking.end_time.is_(None))
        .first()
    )

    if running:
        flash("Auftrag kann nicht gelöscht werden: Es läuft noch eine aktive Buchung.", "danger")
        return redirect(url_for("admin_orders"))

    # abhängige Daten löschen
    TimeBooking.query.filter_by(order_id=o.id).delete()
    QuantityReport.query.filter_by(order_id=o.id).delete()

    db.session.delete(o)
    db.session.commit()

    flash("Auftrag wurde gelöscht.", "success")
    return redirect(url_for("admin_orders"))


@app.route("/admin/orders/import", methods=["GET", "POST"])
@login_required
@role_required("admin")
def admin_orders_import():
    if request.method == "POST":
        file = request.files.get("file")

        if not file or file.filename == "":
            flash("Bitte Excel-Datei auswählen.", "danger")
            return redirect(url_for("admin_orders_import"))

        wb = load_workbook(file, data_only=True)
        ws = wb.active

        # Header lesen
        header = []
        for cell in ws[1]:
            header.append(str(cell.value).strip() if cell.value else "")

        required = ["order_no", "article", "description", "tool_no", "target_qty", "status"]
        for r in required:
            if r not in header:
                flash(f"Spalte fehlt: {r}", "danger")
                return redirect(url_for("admin_orders_import"))

        idx = {name: header.index(name) for name in required}

        created = 0
        skipped = 0

        for row in ws.iter_rows(min_row=2, values_only=True):
            order_no = str(row[idx["order_no"]]).strip() if row[idx["order_no"]] else ""
            if not order_no:
                continue

            # schon vorhanden?
            existing = Order.query.filter_by(order_no=order_no).first()
            if existing:
                skipped += 1
                continue

            article = str(row[idx["article"]]).strip() if row[idx["article"]] else None
            description = str(row[idx["description"]]).strip() if row[idx["description"]] else None
            tool_no = str(row[idx["tool_no"]]).strip() if row[idx["tool_no"]] else None

            try:
                target_qty = int(row[idx["target_qty"]] or 0)
            except:
                target_qty = 0

            status = str(row[idx["status"]]).strip() if row[idx["status"]] else "offen"
            if status not in ["offen", "in_arbeit", "fertig", "gesperrt"]:
                status = "offen"

            o = Order(
                order_no=order_no,
                article=article,
                description=description,
                tool_no=tool_no,
                target_qty=target_qty,
                status=status
            )
            db.session.add(o)
            created += 1

        db.session.commit()

        flash(f"Import fertig: {created} neu, {skipped} übersprungen.", "success")
        return redirect(url_for("admin_orders"))

    return render_template("admin_orders_import.html")


