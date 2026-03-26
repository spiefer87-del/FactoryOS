from flask import redirect, url_for
from flask_login import login_required

from . import bp
from factoryos.extensions import db
from factoryos.modules.masterdata.tools.models import Tool
from ..services.tool_service import delete_tool


@bp.route("/delete/<int:tool_id>")
@login_required
def delete(tool_id):

    tool = Tool.query.get_or_404(tool_id)

    delete_tool(tool)

    return redirect(url_for("tools.list_tools"))
