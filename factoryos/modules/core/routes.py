from flask import Blueprint, redirect, url_for
from flask_login import current_user

bp = Blueprint(
    "core",
    __name__
)


@bp.route("/")
def root():

    if current_user.is_authenticated:
        return redirect(url_for("production.dashboard"))

    return redirect(url_for("auth.login"))
