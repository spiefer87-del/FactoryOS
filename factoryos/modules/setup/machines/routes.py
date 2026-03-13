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
