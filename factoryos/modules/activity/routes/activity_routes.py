from flask import render_template, request
from flask_login import login_required

from ..import bp
from factoryos.core.models.change_log import ChangeLog


@bp.route("/")
@login_required
def list():

    query = ChangeLog.query

    entity_type = request.args.get("type")

    if entity_type:
        query = query.filter_by(entity_type=entity_type)

    logs = query.order_by(ChangeLog.created_at.desc()).limit(50).all()

    return render_template(
        "activity/list.html",
        logs=logs
    )
