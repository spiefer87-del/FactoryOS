from flask import render_template
from flask_login import login_required

from .. import bp
from factoryos.models.tools import ToolMasterdata


@bp.route("/<int:tool_id>")
@login_required
def detail(tool_id):

    tool = ToolMasterdata.query.get_or_404(tool_id)

    return render_template(
        "masterdata/tools/detail.html",
        tool=tool
    )