import os
from werkzeug.utils import secure_filename
from flask import current_app
from factoryos.extensions import db

from factoryos.modules.quality.inspection_plan.models import (
    QualityInspectionIdentificationImage
)

from factoryos.modules.quality.inspection_plan.services.change_log_service import log_change


def upload_identification_image(section, file, description, user_id):

    filename = secure_filename(file.filename)

    upload_folder = os.path.join(
        current_app.static_folder,
        "qm_images"
    )

    os.makedirs(upload_folder, exist_ok=True)

    filepath = os.path.join(upload_folder, filename)

    file.save(filepath)

    image = QualityInspectionIdentificationImage(
        section_id=section.id,
        image_path=f"qm_images/{filename}",
        description=description,
        uploaded_by_id=user_id
    )

    db.session.add(image)

    section.version.is_dirty = True

    log_change(
        section.version,
        "ADD_IMAGE",
        f"Bild zu Modul '{section.title}' hochgeladen"
    )

    db.session.commit()

    return image


def update_image_description(image, new_description):

    section = image.section

    image.description = new_description

    section.version.is_dirty = True

    log_change(
        section.version,
        "UPDATE_IMAGE",
        f"Bildbeschreibung im Modul '{section.title}' geändert"
    )

    db.session.commit()


def delete_identification_image(image):

    section = image.section

    db.session.delete(image)

    section.version.is_dirty = True

    log_change(
        section.version,
        "DELETE_IMAGE",
        f"Bild aus Modul '{section.title}' entfernt"
    )


    db.session.commit()
