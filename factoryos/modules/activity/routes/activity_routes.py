from flask import render_template, request
from flask_login import login_required

from .import bp
from factoryos.core.queries.activity_queries import activity_feed
from factoryos.modules.projects.services.workspace_service import berlin


@bp.route("/")
@login_required
def list():

    entity_type = request.args.get("type")
    logs, activity_types, activity_limit = activity_feed(entity_type, request.args.get('limit', '50'))

    return render_template(
        "activity/list.html",
        logs=logs, activity_types=activity_types, activity_limit=activity_limit, activity_time=berlin
    )
