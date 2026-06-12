from flask import render_template
from flask_login import login_required

from . import bp


@bp.route("/import")
@login_required
def import_errors():

    return render_template(
        "tool_errors/import.html"
    )
