from flask import render_template, request
from flask_login import current_user, login_required

from factoryos.core.auth import has_permission, permission_required
from factoryos.core.queries.change_log_queries import get_logs
from factoryos.core.storage import MATERIAL_DOCUMENT_CATEGORIES
from factoryos.modules.masterdata.shared.constants import (
    MATERIAL_BASE_UNITS,
    MATERIAL_DELIVERY_FORMS,
    MATERIAL_STATUSES,
    MATERIAL_STATUS_COLORS,
    MATERIAL_TYPES,
    POLYMER_TYPES,
)

from ..queries.material_queries import get_material
from ..services.material_storage_service import (
    get_material_storage_path,
    list_material_documents,
)
from . import bp


@bp.route("/<int:material_id>")
@login_required
@permission_required("materials.view")
def detail(material_id):
    material = get_material(material_id)
    limit_param = request.args.get("limit", "5")
    try:
        limit = None if limit_param == "all" else int(limit_param)
    except ValueError:
        limit = 5

    return render_template(
        "masterdata/materials/detail.html",
        material=material,
        documents=list_material_documents(material.material_no),
        storage_path=get_material_storage_path(material.material_no),
        logs=get_logs(entity_type="material", entity_id=material.id, limit=limit),
        MATERIAL_TYPES=MATERIAL_TYPES,
        MATERIAL_STATUSES=MATERIAL_STATUSES,
        MATERIAL_STATUS_COLORS=MATERIAL_STATUS_COLORS,
        POLYMER_TYPES=POLYMER_TYPES,
        MATERIAL_BASE_UNITS=MATERIAL_BASE_UNITS,
        MATERIAL_DELIVERY_FORMS=MATERIAL_DELIVERY_FORMS,
        MATERIAL_DOCUMENT_CATEGORIES=MATERIAL_DOCUMENT_CATEGORIES,
        can_edit=has_permission(current_user, "materials.edit"),
        can_delete=has_permission(current_user, "materials.delete"),
        can_documents=has_permission(current_user, "materials.documents"),
    )
