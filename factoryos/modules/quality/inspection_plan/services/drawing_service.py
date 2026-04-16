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

    db.session.commit()


def upload_snippet(section, file, description):

    filename = secure_filename(file.filename)

    upload_folder = os.path.join(
        current_app.static_folder,
        "qm_snippets"
    )

    os.makedirs(upload_folder, exist_ok=True)

    save_path = os.path.join(upload_folder, filename)

    file.save(save_path)

    snippet = QualityInspectionDimensionSnippet(
        section_id=section.id,
        image_path=f"qm_snippets/{filename}",
        description=description,
        sort_order=len(section.snippets) + 1
    )

    db.session.add(snippet)

    section.version.is_dirty = True

    db.session.commit()

    return snippet


def delete_snippet(snippet):

    db.session.delete(snippet)


    db.session.commit()
