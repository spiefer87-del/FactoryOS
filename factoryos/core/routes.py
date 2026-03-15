
from flask import Blueprint, render_template
from flask_login import login_required

bp = Blueprint(
    "core",
    __name__
)

@bp.route("/")
@login_required
def home():
    return render_template("dashboard.html")

from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user

bp = Blueprint("core", __name__)

@bp.route("/")
def home():

    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))

    return render_template("dashboard/home.html")

