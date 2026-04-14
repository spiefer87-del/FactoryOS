# factoryos/modules/masterdata/tools/services/tool_storage_service.py

import os
import uuid
import shutil

from flask import current_app
from werkzeug.utils import secure_filename

from factoryos.extensions import db
from factoryos.modules.masterdata.tools.models import ToolImage


# =====================================================
# BASIS PFAD
# =====================================================

def get_tool_base_folder(tool_no):
    return os.path.join(
        current_app.static_folder,
        "uploads",
        "tools",
        tool_no
    )


def get_tool_image_folder(tool_no):
    return os.path.join(
        get_tool_base_folder(tool_no),
        "images"
    )


# =====================================================
# ORDNER ERSTELLEN
# =====================================================

def create_tool_folders(tool_no):

    folders = [
        get_tool_image_folder(tool_no),
        os.path.join(get_tool_base_folder(tool_no), "documents"),
        os.path.join(get_tool_base_folder(tool_no), "service"),
        os.path.join(get_tool_base_folder(tool_no), "history"),
    ]

    for folder in folders:
        os.makedirs(folder, exist_ok=True)


# =====================================================
# BILD SPEICHERN
# =====================================================

def save_tool_image(tool, file, title=None, description=None):

    if not file or not file.filename:
        return None

    create_tool_folders(tool.tool_no)

    filename = secure_filename(file.filename)
    filename = f"{uuid.uuid4().hex}_{filename}"

    folder = get_tool_image_folder(tool.tool_no)

    filepath = os.path.join(folder, filename)

    file.save(filepath)

    image = ToolImage(
        tool_id=tool.id,
        image_path=f"uploads/tools/{tool.tool_no}/images/{filename}",
        title=title,
        description=description,
        sort_order=0,
        is_primary=False
    )

    db.session.add(image)

    return image


# =====================================================
# MEHRERE BILDER
# =====================================================

def save_tool_images(tool, files):

    saved = []

    if not files:
        return saved

    for file in files:
        image = save_tool_image(tool, file)

        if image:
            saved.append(image)

    return saved


# =====================================================
# EIN BILD LÖSCHEN
# =====================================================

def delete_tool_image(image):

    if not image:
        return

    filepath = os.path.join(
        current_app.static_folder,
        image.image_path
    )

    if os.path.exists(filepath):
        os.remove(filepath)

    db.session.delete(image)


# =====================================================
# MEHRERE BILDER LÖSCHEN
# =====================================================

def delete_tool_images_by_ids(image_ids):

    if not image_ids:
        return

    for image_id in image_ids:
        img = ToolImage.query.get(image_id)

        if img:
            delete_tool_image(img)


# =====================================================
# KOMPLETTEN ORDNER LÖSCHEN
# =====================================================

def delete_tool_folder(tool_no):

    folder = get_tool_base_folder(tool_no)

    if os.path.exists(folder):
        shutil.rmtree(folder)


# =====================================================
# ORDNER UMBENENNEN
# =====================================================

def rename_tool_folder(old_tool_no, new_tool_no):

    if old_tool_no == new_tool_no:
        return

    old_folder = get_tool_base_folder(old_tool_no)
    new_folder = get_tool_base_folder(new_tool_no)

    if os.path.exists(old_folder):
        os.rename(old_folder, new_folder)

    # DB Pfade aktualisieren
    images = ToolImage.query.join(
        ToolImage.tool
    ).filter_by(tool_no=new_tool_no).all()

    for img in images:
        img.image_path = img.image_path.replace(
            f"uploads/tools/{old_tool_no}/",
            f"uploads/tools/{new_tool_no}/"
        )
