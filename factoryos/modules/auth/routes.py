from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user
from factoryos.models.user import User

bp = Blueprint("auth", __name__)

@bp.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username, active=True).first()

        if not user or not user.check_password(password):
            flash("Login fehlgeschlagen.", "danger")
            return redirect(url_for("auth.login"))

        login_user(user)

        return redirect(url_for("production.dashboard"))

    return render_template("login.html")

@bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
