from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required

from factoryos.extensions import db
from factoryos.models.user import User
from factoryos.modules.admin.roles.models import Role

from .user_routes import bp


@bp.route("/create", methods=["GET", "POST"])
@login_required
def create_user():

    roles = Role.query.filter_by(active=True).order_by(Role.name).all()

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")
        role_id = request.form.get("role_id")

        existing_user = User.query.filter_by(username=username).first()

        if existing_user:
            flash("Benutzername existiert bereits", "error")
            return redirect(url_for("admin_users.create_user"))

        user = User(
            username=username,
            role_id=role_id,
            active=True
        )

        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash("Benutzer erfolgreich angelegt", "success")

        return redirect(url_for("admin_users.list_users"))

    return render_template(
        "admin/users/create.html",
        roles=roles
    )