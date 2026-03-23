from flask import render_template
from flask_login import login_required

from . import bp
from factoryos.modules.masterdata.tools.models import Tool


@bp.route("/<int:tool_id>")
@login_required
def detail(tool_id):

    tool = Tool.query.get_or_404(tool_id)

    return render_template(
        "masterdata/tools/detail.html",
        tool=tool
    )
