from flask import request, redirect
from flask_login import login_required

from factoryos.extensions import db

from factoryos.modules.quality.inspection_plan.models import (
    QualityInspectionSection,
    QualityInspectionGaugeCheck
)

from factoryos.modules.quality.inspection_plan.change_log_service import (
    log_change
)

from . import bp


# --------------------------------------------------
# Add Gauge Check
# --------------------------------------------------

@bp.route("/section/<int:section_id>/add_gauge_check", methods=["POST"])
@login_required
def quality_add_gauge_check(section_id):

    section = QualityInspectionSection.query.get_or_404(section_id)

    if section.version.status != "draft":
        return redirect(request.referrer or url_for("inspection.quality_inspection_plan"))

    last = (
        QualityInspectionGaugeCheck.query
        .filter_by(section_id=section.id)
        .order_by(QualityInspectionGaugeCheck.sort_order.desc())
        .first()
    )

    order = 1

    if last:
        order = last.sort_order + 1

    check = QualityInspectionGaugeCheck(
        section_id=section.id,
        name=request.form.get("name"),
        gauge_id=request.form.get("gauge_id"),
        method=request.form.get("method"),
        sort_order=order
    )

    db.session.add(check)

    section.version.is_dirty = True

    log_change(
        section.version,
        "ADD_GAUGE_CHECK",
        f"Lehrenprüfung '{check.name}' hinzugefügt"
    )

    db.session.commit()

    return redirect(request.referrer or url_for("inspection.quality_inspection_plan"))
