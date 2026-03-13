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
