from flask import render_template, request
from flask_login import current_user, login_required

from factoryos.core.auth import has_permission, permission_required
from factoryos.modules.masterdata.shared.constants import (
    MATERIAL_STATUSES,
    MATERIAL_STATUS_COLORS,
    MATERIAL_TYPES,
    POLYMER_TYPES,
)

from ..queries.material_queries import get_materials
from . import bp


@bp.route("/list")
@login_required
@permission_required("materials.view")
def list_materials():
    return render_template(
        "masterdata/materials/list.html",
        materials=get_materials(
            search=request.args.get("search", "").strip(),
            material_type=request.args.get("material_type", "").strip(),
            status=request.args.get("status", "").strip(),
        ),
        MATERIAL_TYPES=MATERIAL_TYPES,
        MATERIAL_STATUSES=MATERIAL_STATUSES,
        MATERIAL_STATUS_COLORS=MATERIAL_STATUS_COLORS,
        POLYMER_TYPES=POLYMER_TYPES,
        can_create=has_permission(current_user, "materials.create"),
        can_edit=has_permission(current_user, "materials.edit"),
        can_delete=has_permission(current_user, "materials.delete"),
    )
