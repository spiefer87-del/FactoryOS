from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user

from factoryos.models.user import User


bp = Blueprint(
    "auth",
    __name__
)


# --------------------------------------------------
# LOGIN
# --------------------------------------------------

@bp.route("/login", methods=["GET", "POST"])
def login():

    # Wenn bereits eingeloggt → Dashboard
    if current_user.is_authenticated:
        return redirect(url_for("core.home"))

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        user = User.query.filter_by(username=username, active=True).first()

        if not user or not user.check_password(password):

            flash("Login fehlgeschlagen.", "danger")
            return redirect(url_for("auth.login"))

        login_user(user)

        flash("Erfolgreich eingeloggt.", "success")

        return redirect(url_for("core.home"))

    return render_template("auth/login.html")


# --------------------------------------------------
# LOGOUT
# --------------------------------------------------

@bp.route("/logout")
@login_required
def logout():

    logout_user()

    flash("Du wurdest ausgeloggt.", "info")

    return redirect(url_for("auth.login"))