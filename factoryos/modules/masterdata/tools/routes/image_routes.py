from factoryos.core.services.change_log_service import log_change
from flask import redirect, url_for
from flask_login import login_required

from . import bp
from factoryos.extensions import db
from factoryos.modules.masterdata.tools.models import ToolImage


@bp.route("/image-primary/<int:image_id>")
@login_required
def image_primary(image_id):

    image = ToolImage.query.get_or_404(image_id)

    changed=not image.is_primary
    ToolImage.query.filter_by(
        tool_id=image.tool_id
    ).update({"is_primary": False})

    image.is_primary = True

    if changed:log_change("tool",image.tool_id,"image_primary",{"primary_image":image.title or f"Bild #{image.id}"},category="images",entity_name=image.tool.tool_no)
    db.session.commit()

    return redirect(
        url_for("tools.edit", tool_id=image.tool_id)
    )
