from flask import Blueprint, render_template
from flask_login import login_required

bp = Blueprint(
    "articles",
    __name__,
    url_prefix="/masterdata/articles"
)


@bp.route("/")
@login_required
def dashboard():

    return render_template("masterdata/articles/dashboard.html")