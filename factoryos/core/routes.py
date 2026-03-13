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
