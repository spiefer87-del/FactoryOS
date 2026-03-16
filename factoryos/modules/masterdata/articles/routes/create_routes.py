from flask import render_template
from flask_login import login_required
from . import bp


@bp.route("/create")
@login_required
def create():
    return render_template("masterdata/articles/create.html")
