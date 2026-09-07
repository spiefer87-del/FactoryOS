from flask import flash, redirect, url_for
from flask_login import login_required

from factoryos.core.auth import permission_required

from ..queries.material_queries import get_material
from ..services.material_service import delete_material
from . import bp


@bp.route("/<int:material_id>/delete", methods=["POST"])
@login_required
@permission_required("materials.delete")
def delete(material_id):
    material = get_material(material_id)
    delete_material(material)
    flash("Material wurde gelöscht; die Ablage wurde archiviert.", "success")
    return redirect(url_for("materials.list_materials"))
