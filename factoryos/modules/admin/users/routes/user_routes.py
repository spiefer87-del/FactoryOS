from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required
from factoryos.extensions import db
from factoryos.models.user import User

bp = Blueprint(
    "admin_users",
    __name__,
    url_prefix="/admin/users"
)


@bp.route("/", methods=["GET", "POST"])
@login_required
def list_users():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")
        role = request.form.get("role")

        user = User(
            username=username,
            role=role
        )

        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        return redirect(url_for("admin_users.list_users"))

    users = User.query.all()

    return render_template(
        "admin/users/user.html",
        users=users
    )