import os
from werkzeug.utils import secure_filename
from flask import current_app
from factoryos.extensions import db

from ..models import QualityInspectionIdentificationImage

from factoryos.modules.quality.inspection_plan.services.change_log_service import log_change


def upload_identification_image(section, file, description, user_id):

    from uuid import uuid4
    from PIL import Image as PILImage, ImageOps, UnidentifiedImageError
    from flask import abort
    filename = str(uuid4())+'.png'
    try:
        photo=PILImage.open(file.stream)
        if photo.format not in ('JPEG','PNG','WEBP') or photo.width*photo.height>24000000:
            abort(400,'Referenzbild: JPEG/PNG/WebP bis 24 Megapixel verwenden.')
        photo.load();photo=ImageOps.exif_transpose(photo).convert('RGB');photo.thumbnail((1800,1800))
    except (UnidentifiedImageError, OSError, PILImage.DecompressionBombError):
        abort(400,'Referenzbild konnte nicht gelesen werden. Bitte ein gültiges Foto auswählen.')

    upload_folder = os.path.join(
        current_app.static_folder,
        "qm_identification"
    )

    os.makedirs(upload_folder, exist_ok=True)

    filepath = os.path.join(upload_folder, filename)

    photo.save(filepath,'PNG')

    image = QualityInspectionIdentificationImage(
        section_id=section.id,
        image_path=f"qm_identification/{filename}",
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
