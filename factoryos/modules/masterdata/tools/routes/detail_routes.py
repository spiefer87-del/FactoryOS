from flask import render_template
from flask_login import login_required

from . import bp
from factoryos.modules.masterdata.tools.models import Tool
from factoryos.modules.masterdata.tools.queries.tool_queries import get_tool_logs

@bp.route("/<int:tool_id>")
@login_required
def detail(tool_id):

    tool = Tool.query.get_or_404(tool_id)
    logs = get_tool_logs(tool_id)

    return render_template(
        "masterdata/tools/detail.html",
        tool=tool,
        logs=logs   # 🔥 WICHTIG
    )
