from flask import Blueprint, render_template
from flask_login import login_required

from . import bp

@bp.route("/")
@login_required
def dashboard():

    return render_template("masterdata/articles/dashboard.html")
