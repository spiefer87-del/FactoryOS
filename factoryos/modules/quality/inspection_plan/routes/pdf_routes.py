from flask import redirect, url_for, send_file
from flask_login import login_required

from factoryos.extensions import db
from ..models import QualityInspectionPlanVersion
from factoryos.modules.quality.inspection_plan.services.pdf_service import generate_inspection_plan_pdf

from . import bp

import os

@bp.route("/export_pdf/<int:version_id>")
@login_required
def quality_export_pdf(version_id):

    version = QualityInspectionPlanVersion.query.get_or_404(version_id)

    pdf_path = generate_inspection_plan_pdf(version_id)

    version.pdf_path = pdf_path
    db.session.commit()

    full_path = os.path.join(
        current_app.static_folder,
        pdf_path
    )

    return send_file(
        full_path,
        as_attachment=True,
        download_name=f"Pruefplan_Rev_{version.revision}.pdf"
    )
