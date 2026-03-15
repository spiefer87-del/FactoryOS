import os

from flask import request, redirect, jsonify, current_app
from flask_login import login_required

from factoryos.modules.quality.inspection_plan.models import (
    QualityInspectionSection,
    QualityInspectionDimensionSnippet
)

from factoryos.modules.quality.inspection_plan.services.drawing_service import (
    upload_drawing,
    upload_snippet,
    delete_snippet
)

from factoryos.modules.quality.inspection_plan.services.feature_detection_service import (
    detect_drawing_features
)

from . import bp


# --------------------------------------------------
# Upload Drawing
# --------------------------------------------------

@bp.route("/section/<int:section_id>/upload_drawing", methods=["POST"])
@login_required
def quality_upload_drawing(section_id):

    section = QualityInspectionSection.query.get_or_404(section_id)

    file = request.files.get("drawing")

    if not file:
        return redirect(request.referrer or url_for("inspection.quality_inspection_plan"))

    upload_drawing(section, file)

    return redirect(request.referrer or url_for("inspection.quality_inspection_plan"))


# --------------------------------------------------
# Upload Snippet
# --------------------------------------------------

@bp.route("/section/<int:section_id>/upload_snippet", methods=["POST"])
@login_required
def quality_upload_snippet(section_id):

    section = QualityInspectionSection.query.get_or_404(section_id)

    if section.version.status != "draft":
        return redirect(request.referrer or url_for("inspection.quality_inspection_plan"))

    file = request.files.get("snippet")

    upload_snippet(
        section,
        file,
        request.form.get("description")
    )

    return redirect(request.referrer or url_for("inspection.quality_inspection_plan"))


# --------------------------------------------------
# Delete Snippet
# --------------------------------------------------

@bp.route("/snippet/<int:snippet_id>/delete", methods=["POST"])
@login_required
def quality_delete_snippet(snippet_id):

    snippet = QualityInspectionDimensionSnippet.query.get_or_404(snippet_id)

    delete_snippet(snippet)

    return redirect(request.referrer or url_for("inspection.quality_inspection_plan"))


# --------------------------------------------------
# Detect Drawing Features
# --------------------------------------------------

@bp.route("/detect_features/<int:section_id>")
@login_required
def detect_features(section_id):

    section = QualityInspectionSection.query.get_or_404(section_id)

    if not section.drawing_path:
        return jsonify([])

    img_path = os.path.join(
        current_app.static_folder,
        section.drawing_path
    )

    circles = detect_drawing_features(img_path)

    return jsonify(circles)
