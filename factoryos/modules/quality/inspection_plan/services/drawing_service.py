from .change_log_service import log_change
import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app
from factoryos.extensions import db

from PIL import Image as PILImage
from pdf2image import convert_from_path

from factoryos.modules.quality.inspection_plan.models import (
    QualityInspectionDimensionSnippet
)

from factoryos.core.image_engine import save_standard_image

def upload_drawing(section, file):

    filename = secure_filename(file.filename)

    ext = filename.rsplit(".", 1)[-1].lower()

    # ==========================================
    # PDF UPLOAD
    # ==========================================

    if ext == "pdf":

        upload_folder = os.path.join(
            current_app.static_folder,
            "qm_drawings"
        )

        os.makedirs(upload_folder, exist_ok=True)

        pdf_filename = f"{uuid.uuid4()}.pdf"

        pdf_path = os.path.join(
            upload_folder,
            pdf_filename
        )

        file.save(pdf_path)

        # erste Seite rendern
        pages = convert_from_path(
            pdf_path,
            dpi=300,
            first_page=1,
            last_page=1,
            poppler_path="/usr/bin"
        )

        image = pages[0]

        image = image.convert("RGB")

        image.thumbnail(
            (1600, 1200),
            PILImage.Resampling.LANCZOS
        )

        png_filename = f"{uuid.uuid4()}.png"

        png_path = os.path.join(
            upload_folder,
            png_filename
        )

        image.save(
            png_path,
            "PNG"
        )

        section.drawing_path = (
            f"qm_drawings/{png_filename}"
        )

        section.image_width = 1600
        section.image_height = 1200

    # ==========================================
    # NORMALER BILDUPLOAD
    # ==========================================

    else:

        result = save_standard_image(
            file=file,
            subfolder="qm_drawings",
            max_size=(1600, 1200),
            create_thumb=False,
            fixed_canvas=True
        )

        section.drawing_path = result["path"]

        section.image_width = 1600
        section.image_height = 1200

    section.version.is_dirty = True
    log_change(section.version,"DRAWING",f"Zeichnung in Modul {section.title} aktualisiert")
    db.session.commit()


def upload_snippet(section, file, description):

    from flask import abort
    from PIL import ImageOps, UnidentifiedImageError
    if not file:abort(400,'Zeichnungsausschnitt: Bitte ein Bild auswählen.')
    try:
        photo=PILImage.open(file.stream)
        if photo.format not in ('JPEG','PNG','WEBP') or photo.width*photo.height>24000000:
            abort(400,'Zeichnungsausschnitt: JPEG/PNG/WebP bis 24 Megapixel verwenden.')
        photo.load();photo=ImageOps.exif_transpose(photo).convert('RGB');photo.thumbnail((1800,1800))
    except (UnidentifiedImageError,OSError,PILImage.DecompressionBombError):
        abort(400,'Zeichnungsausschnitt konnte nicht gelesen werden.')
    filename = str(uuid.uuid4())+'.png'

    upload_folder = os.path.join(
        current_app.static_folder,
        "qm_snippets"
    )

    os.makedirs(upload_folder, exist_ok=True)

    save_path = os.path.join(upload_folder, filename)

    photo.save(save_path,'PNG')

    snippet = QualityInspectionDimensionSnippet(
        section_id=section.id,
        image_path=f"qm_snippets/{filename}",
        description=description,
        sort_order=len(section.snippets) + 1
    )

    db.session.add(snippet)

    section.version.is_dirty = True
    log_change(section.version,"ADD_SNIPPET",f"Zeichnungsausschnitt in {section.title} ergänzt: {description or 'Ohne Beschreibung'}")
    db.session.commit()

    return snippet


def delete_snippet(snippet):
    snippet.section.version.is_dirty=True
    log_change(snippet.section.version,"DELETE_SNIPPET",f"Zeichnungsausschnitt aus {snippet.section.title} entfernt")
    db.session.delete(snippet)


    db.session.commit()
