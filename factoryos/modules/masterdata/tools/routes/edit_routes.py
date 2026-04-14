from flask import render_template, request, redirect, url_for
from flask_login import login_required

from . import bp
from ..services.tool_service import update_tool
from factoryos.modules.masterdata.tools.models import Tool
from factoryos.modules.masterdata.shared.constants import TOOL_STATUSES


@bp.route("/edit/<int:tool_id>", methods=["GET", "POST"])
@login_required
def edit(tool_id):

    tool = Tool.query.get_or_404(tool_id)

    if request.method == "POST":

        files = request.files.getlist("images")
        delete_ids = request.form.getlist("delete_images")

        update_tool(
            tool,
            request.form,
            files,
            delete_ids
        )

        return redirect(
            url_for("tools.list_tools")
        )

    return render_template(
        "masterdata/tools/edit.html",
        tool=tool,
        TOOL_STATUSES=TOOL_STATUSES
    )
