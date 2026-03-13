from flask import render_template
from flask_login import login_required

from . import bp


@bp.route("/")
@login_required
def quality_dashboard():
    return render_template("quality/dashboard.html")
