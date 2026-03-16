from flask import render_template, request, redirect, url_for
from flask_login import login_required

from . import bp



@bp.route("/create", methods=["GET", "POST"])
@login_required
def create():

    if request.method == "POST":

        create_tool(request.form)

        return redirect(
            url_for("tools.list_tools")
        )

    return render_template(
        "masterdata/tools/create.html"
    )
