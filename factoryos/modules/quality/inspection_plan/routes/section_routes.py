from flask import request, redirect
from flask_login import login_required

from factoryos.modules.quality.inspection_plan.models import QualityInspectionSection
from factoryos.modules.quality.inspection_plan.section_service import (
    delete_section,
    add_characteristic
)

from . import bp


@bp.route("/section/<int:section_id>/delete", methods=["POST"])
@login_required
def quality_delete_section(section_id):

    section = QualityInspectionSection.query.get_or_404(section_id)

    if section.version.status != "draft":
        return redirect(request.referrer)

    delete_section(section)

    return redirect(request.referrer)


@bp.route("/section/<int:section_id>/add_characteristic", methods=["POST"])
@login_required
def quality_add_characteristic(section_id):

    section = QualityInspectionSection.query.get_or_404(section_id)

    if section.version.status != "draft":
        return redirect(request.referrer)

    add_characteristic(section, request.form)

    return redirect(request.referrer)
