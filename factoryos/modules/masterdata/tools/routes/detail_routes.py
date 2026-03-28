from flask import render_template
from flask_login import login_required

from . import bp
from factoryos.modules.masterdata.tools.models import Tool
from factoryos.core.queries.change_log_queries import get_logs



@bp.route("/<int:tool_id>")
@login_required
def detail(tool_id):

    tool = Tool.query.get_or_404(tool_id)
    logs = get_logs(
        entity_type="tool",
        entity_id=tool.id,
        limit=request.args.get("limit", 5)
    )

    return render_template(
        "masterdata/tools/detail.html",
        tool=tool,
        logs=logs   # 🔥 WICHTIG
    )
