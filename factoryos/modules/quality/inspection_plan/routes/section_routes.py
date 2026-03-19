from flask import request, redirect, url_for
from flask_login import login_required

from ..models import QualityInspectionSection
from factoryos.modules.quality.inspection_plan.services.section_service import *
from factoryos.modules.quality.inspection_plan.services.characteristic_service import *
from factoryos.modules.quality.inspection_plan.services.marker_service import *

from . import bp


@bp.route("/section/<int:section_id>/delete", methods=["POST"])
@login_required
def quality_delete_section(section_id):

    section = QualityInspectionSection.query.get_or_404(section_id)

    if section.version.status != "draft":
        return redirect(request.referrer or url_for("inspection.quality_inspection_plan"))

    delete_section(section)

    return redirect(request.referrer or url_for("inspection.quality_inspection_plan"))

@bp.route("/section/<int:section_id>/add_characteristic", methods=["POST"])
@login_required
def quality_add_characteristic(section_id):

    section = QualityInspectionSection.query.get_or_404(section_id)

    add_characteristic(section, request.form)

    return redirect(
        url_for(
            "inspection.quality_version_edit",
            plan_id=section.version.plan_id,
            plan_version_id=section.version.id
        )
    )
