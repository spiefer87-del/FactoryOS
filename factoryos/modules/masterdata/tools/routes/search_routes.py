from flask import request, jsonify
from flask_login import login_required

from . import bp
from ..queries.tool_queries import search_tools


@bp.route("/api/search")
@login_required
def search():

    q = request.args.get("q", "")

    tools = search_tools(q)

    return jsonify({
        "results": [
            {
                "id": t.id,
                "text": f"{t.tool_no} - {t.description or ''}"
            }
            for t in tools
        ]
    })