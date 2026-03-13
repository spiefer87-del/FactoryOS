from flask import request, redirect
from flask_login import login_required, current_user

from factoryos.modules.quality.inspection_plan.models import (
    QualityInspectionSection,
    QualityInspectionIdentificationImage
)

from factoryos.modules.quality.inspection_plan.image_service import (
    upload_identification_image,
    update_image_description,
    delete_identification_image
)

from . import bp


# --------------------------------------------------
# Upload Identification Image
# --------------------------------------------------

@bp.route("/section/<int:section_id>/upload_image", methods=["POST"])
@login_required
def quality_upload_identification_image(section_id):

    section = QualityInspectionSection.query.get_or_404(section_id)

    if section.section_type != "identification":
        
return redirect(request.referrer or url_for("inspection.quality_inspection_plan"))
    if section.version.status != "draft":
        return redirect(request.referrer)

    if len(section.images) >= 5:
        return redirect(request.referrer)

    file = request.files.get("image")

    if not file:
        return redirect(request.referrer)

    upload_identification_image(
        section,
        file,
        request.form.get("description"),
        current_user.id
    )

    return redirect(request.referrer)


# --------------------------------------------------
# Update Image Description
# --------------------------------------------------

@bp.route("/image/<int:image_id>/update_description", methods=["POST"])
@login_required
def quality_update_image_description(image_id):

    image = QualityInspectionIdentificationImage.query.get_or_404(image_id)

    section = image.section

    if section.version.status != "draft":
        return redirect(request.referrer)

    update_image_description(
        image,
        request.form.get("description")
    )

    return redirect(request.referrer)


# --------------------------------------------------
# Delete Image
# --------------------------------------------------

@bp.route("/image/<int:image_id>/delete", methods=["POST"])
@login_required
def quality_delete_identification_image(image_id):

    image = QualityInspectionIdentificationImage.query.get_or_404(image_id)

    section = image.section

    if section.version.status != "draft":
        return redirect(request.referrer)

    delete_identification_image(image)

    return redirect(request.referrer)
