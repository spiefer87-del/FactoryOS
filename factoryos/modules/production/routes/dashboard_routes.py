from flask import render_template
from flask_login import login_required

from . import bp


@bp.route("/")
@login_required
def dashboard():

    return render_template(
        "production/dashboard.html"
    )


@bp.route("/booking")
@login_required
def booking_dashboard():

    return render_template(
        "production/booking/dashboard.html"
    )
