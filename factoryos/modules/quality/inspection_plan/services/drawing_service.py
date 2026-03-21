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



def upload_drawing(section, file):

    filename = secure_filename(file.filename)
    ext = filename.lower().split(".")[-1]

    unique = f"{uuid.uuid4()}_{filename}"

    upload_folder = os.path.join(
        current_app.static_folder,
        "qm_drawings"
    )

    os.makedirs(upload_folder, exist_ok=True)

    save_path = os.path.join(upload_folder, unique)

    file.save(save_path)

    # 🔥 HIER EINFÜGEN (GANZ WICHTIG!)
    from PIL import Image as PILImage

    

    # =============================

    preview_filename = unique + ".png"
    preview_path = os.path.join(upload_folder, preview_filename)

    

    from PIL import Image as PILImage

    TARGET_WIDTH = 800  # 🔥 hier steuerst du alles!
    
    # ================================
    # PREVIEW ERZEUGEN + NORMALISIEREN
    # ================================
    
    if ext == "pdf":
    
        pages = convert_from_path(save_path, dpi=300)
        img = pages[0]
    
    else:
    
        img = PILImage.open(save_path)
    
    # 🔥 IMMER RGB
    img = img.convert("RGB")
    
    # 🔥 SKALIEREN (SEHR WICHTIG)
    ratio = TARGET_WIDTH / img.width
    new_height = int(img.height * ratio)
    
    img = img.resize((TARGET_WIDTH, new_height), PILImage.LANCZOS)
    
    # 🔥 SPEICHERN
    img.save(preview_path, "PNG")
    
    img = PILImage.open(preview_path)
    
    section.image_width = img.width
    section.image_height = img.height

    section.drawing_path = f"qm_drawings/{preview_filename}"

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
