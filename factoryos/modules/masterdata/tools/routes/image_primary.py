from flask import redirect, url_for
from flask_login import login_required

from . import bp
from factoryos.extensions import db
from factoryos.modules.masterdata.tools.models import ToolImage


@bp.route("/image-primary/<int:image_id>")
@login_required
def image_primary(image_id):

    image = ToolImage.query.get_or_404(image_id)

    ToolImage.query.filter_by(
        tool_id=image.tool_id
    ).update({"is_primary": False})

    image.is_primary = True

    db.session.commit()

    return redirect(
        url_for("tools.edit", tool_id=image.tool_id)
    )
