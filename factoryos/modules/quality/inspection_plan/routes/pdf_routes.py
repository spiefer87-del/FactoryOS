from flask import redirect, url_for
from flask_login import login_required

from factoryos.extensions import db
from ..models import QualityInspectionPlanVersion
from factoryos.modules.quality.inspection_plan.services.pdf_service import generate_inspection_plan_pdf

from . import bp


@bp.route("/export_pdf/<int:version_id>")
@login_required
def quality_export_pdf(version_id):

    pdf_path = generate_inspection_plan_pdf(version_id)

    version = QualityInspectionPlanVersion.query.get_or_404(version_id)

    version.pdf_path = pdf_path

    db.session.commit()

    return redirect(
        url_for(
            "inspection.quality_version_edit",
            plan_id=version.plan_id,
            plan_version_id=version.id
        )
    )
