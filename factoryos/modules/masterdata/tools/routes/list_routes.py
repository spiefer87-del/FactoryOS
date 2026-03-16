from flask import render_template, request
from flask_login import login_required
from ..queries.tool_queries import get_tools
from . import bp


@bp.route("/list")
@login_required
def list_tools():

    search = request.args.get("search", "").strip()
    status = request.args.get("status", "")
    location = request.args.get("location", "")

    tools, statuses, locations = get_tools(
        search,
        status,
        location
    )

    return render_template(
        "masterdata/tools/list.html",
        tools=tools,
        search=search,
        status=status,
        location=location,
        statuses=statuses,
        locations=locations
    )
