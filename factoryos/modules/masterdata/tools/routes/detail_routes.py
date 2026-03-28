from flask import render_template, request
from flask_login import login_required

from . import bp
from factoryos.modules.masterdata.tools.models import Tool
from factoryos.core.queries.change_log_queries import get_logs
from ..queries.tool_queries import get_tools



@bp.route("/<int:tool_id>")
@login_required
def detail(tool_id):

    tool = get_tools(tool_id)

    # 🔥 Limit sauber behandeln
    limit_param = request.args.get("limit", "5")

    if limit_param == "all":
        limit = None
    else:
        try:
            limit = int(limit_param)
        except ValueError:
            limit = 5  # fallback

    # 🔥 Logs laden
    logs = get_logs(
        entity_type="tool",
        entity_id=tool.id,
        limit=limit
    )

    return render_template(
        "masterdata/tools/detail.html",
        tool=tool,
        logs=logs   # 🔥 WICHTIG
    )
