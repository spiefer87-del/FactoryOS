from flask import render_template, request
from flask_login import login_required

from . import bp
from factoryos.core.queries.change_log_queries import get_logs
from ..queries.tool_queries import get_tool
from ..services.tool_storage_service import (
    DOCUMENT_CATEGORIES,
    get_tool_storage_path,
    list_tool_documents,
)

from factoryos.modules.masterdata.shared.constants import TOOL_STATUSES

@bp.route("/<int:tool_id>")
@login_required
def detail(tool_id):

    tool = get_tool(tool_id)

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
        logs=logs,
        TOOL_STATUSES=TOOL_STATUSES,
        documents=list_tool_documents(tool.tool_no),
        DOCUMENT_CATEGORIES=DOCUMENT_CATEGORIES,
        storage_path=get_tool_storage_path(tool.tool_no)
    )
