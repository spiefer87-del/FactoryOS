from flask import render_template, request, redirect, url_for
from flask_login import login_required

from .. import bp
from ..services.tool_service import update_tool
from factoryos.models.tools import ToolMasterdata


@bp.route("/edit/<int:tool_id>", methods=["GET", "POST"])
@login_required
def edit(tool_id):

    tool = ToolMasterdata.query.get_or_404(tool_id)

    if request.method == "POST":

        update_tool(tool, request.form)

        return redirect(
            url_for("tools.list_tools")
        )

    return render_template(
        "masterdata/tools/edit.html",
        tool=tool
    )