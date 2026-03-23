from flask import redirect, url_for
from flask_login import login_required

from . import bp
from factoryos.extensions import db
from factoryos.modules.masterdata.tools.models import Tool


@bp.route("/delete/<int:tool_id>")
@login_required
def delete(tool_id):

    tool = Tool.query.get_or_404(tool_id)

    db.session.delete(tool)
    db.session.commit()

    return redirect(url_for("tools.list_tools"))
