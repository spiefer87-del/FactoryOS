from flask import redirect, url_for, send_file, current_app
from flask_login import login_required

from factoryos.extensions import db
from ..models import QualityInspectionPlanVersion
from factoryos.modules.quality.inspection_plan.services.pdf_service import generate_inspection_plan_pdf, export_section_drawing

from . import bp

import os

@bp.route("/export_pdf/<int:version_id>")
@login_required
def quality_export_pdf(version_id):

    version = QualityInspectionPlanVersion.query.get_or_404(version_id)

    output = generate_inspection_plan_pdf(version_id)
    from werkzeug.utils import secure_filename

    return send_file(
        output,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=secure_filename(f"{version.plan.tool.tool_no}_Pruefplan_Rev_{version.revision}.pdf")
    )



@bp.route("/export-section-drawing/<int:section_id>")
@login_required
def quality_export_section_drawing(section_id):

    return export_section_drawing(section_id)
