from flask import render_template, request, redirect, url_for
from flask_login import login_required

from . import bp
from ..services.tool_service import create_tool
from factoryos.modules.masterdata.shared.constants import TOOL_STATUSES


@bp.route("/create", methods=["GET", "POST"])
@login_required
def create():

    if request.method == "POST":

        create_tool(request.form)

        return redirect(
            url_for("tools.list_tools")
        )

    return render_template(
        "masterdata/tools/create.html",
        TOOL_STATUSES=TOOL_STATUSES
    )
