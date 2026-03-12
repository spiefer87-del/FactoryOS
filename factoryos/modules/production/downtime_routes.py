bp = Blueprint(
    "production_downtime",
    __name__,
    url_prefix="/production/downtime"
)

@bp.route("/reasons")
@login_required
@role_required("admin", "schichtleiter")
def downtime_reasons():
    reasons = DowntimeReason.query.order_by(DowntimeReason.name.asc()).all()
    return render_template("admin_reasons.html", reasons=reasons)


@bp.route("/reasons/create", methods=["GET", "POST"])
@login_required
@role_required("admin")
def downtime_reasons_create():
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

@bp.route("/reasons/edit/<int:reason_id>", methods=["GET", "POST"])
@login_required
@role_required("admin")
def downtime_reasons_edit(reason_id):
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

@bp.route("/reasons/toggle/<int:reason_id>", methods=["POST"])
@login_required
@role_required("admin")
def downtime_reasons_toggle(reason_id):
    r = DowntimeReason.query.get_or_404(reason_id)
    r.active = not r.active
    db.session.commit()

    flash("Störgrundstatus geändert.", "success")
    return redirect(url_for("admin_reasons"))
