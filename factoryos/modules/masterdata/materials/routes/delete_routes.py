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
    from factoryos.modules.masterdata.articles.models import Article
    if Article.query.filter((Article.material_id == material.id) | (Article.masterbatch_id == material.id)).first():
        flash("Dieses Material ist Artikeln zugeordnet. Bitte zuerst die Rohstoffzuordnung entfernen.", "warning")
        return redirect(url_for("materials.detail", material_id=material.id))
    from factoryos.modules.sampling.models import SamplingOrder
    if SamplingOrder.query.filter((SamplingOrder.material_id == material.id) | (SamplingOrder.data["masterbatch_id"].as_integer() == material.id)).first():
        flash("Dieser Stammdatensatz wird von einem Musterungsauftrag verwendet und kann nicht gelöscht werden.", "warning")
        return redirect(url_for("materials.detail", material_id=material.id))
    delete_material(material)
    flash("Material wurde gelöscht; die Ablage wurde archiviert.", "success")
    return redirect(url_for("materials.list_materials"))
