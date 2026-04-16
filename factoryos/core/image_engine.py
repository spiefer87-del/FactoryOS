# factoryos/core/image_engine.py

import os
import uuid
from PIL import Image, ImageOps

# =====================================================
# CONFIG
# =====================================================

UPLOAD_ROOT = "factoryos/static/uploads"

DEFAULT_MAX_SIZE = (1600, 1200)
THUMB_SIZE = (400, 300)

JPEG_QUALITY = 85


# =====================================================
# HELPERS
# =====================================================

def ensure_folder(path):
    os.makedirs(path, exist_ok=True)


def generate_filename(original_name, ext=".jpg"):
    uid = uuid.uuid4().hex[:16]
    return f"{uid}{ext}"


def normalize_image(img: Image.Image):
    """
    EXIF drehen + RGB sicherstellen
    """
    img = ImageOps.exif_transpose(img)

    if img.mode in ("RGBA", "P"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
        img = background
    else:
        img = img.convert("RGB")

    return img


def resize_contain(img: Image.Image, max_size):
    """
    Bild proportional verkleinern
    """
    img.thumbnail(max_size, Image.LANCZOS)
    return img


def resize_canvas(img: Image.Image, canvas_size):
    """
    Bild mittig auf weiße Fläche setzen
    """
    canvas = Image.new("RGB", canvas_size, (255, 255, 255))

    x = (canvas_size[0] - img.width) // 2
    y = (canvas_size[1] - img.height) // 2

    canvas.paste(img, (x, y))
    return canvas


# =====================================================
# MAIN SAVE FUNCTION
# =====================================================

def save_standard_image(
    file,
    subfolder,
    max_size=DEFAULT_MAX_SIZE,
    create_thumb=True,
    fixed_canvas=True
):
    """
    Universal Upload Engine

    returns:
        {
            "path": "...",
            "thumb": "...",
            "filename": "..."
        }
    """

    folder = os.path.join(UPLOAD_ROOT, subfolder)
    ensure_folder(folder)

    filename = generate_filename(file.filename)
    filepath = os.path.join(folder, filename)

    img = Image.open(file)
    img = normalize_image(img)
    img = resize_contain(img, max_size)

    if fixed_canvas:
        img = resize_canvas(img, max_size)

    img.save(filepath, quality=JPEG_QUALITY, optimize=True)

    result = {
        "filename": filename,
        "path": f"uploads/{subfolder}/{filename}",
        "thumb": None
    }

    # Thumbnail
    if create_thumb:
        thumb_name = filename.replace(".jpg", "_thumb.jpg")
        thumb_path = os.path.join(folder, thumb_name)

        thumb = img.copy()
        thumb.thumbnail(THUMB_SIZE, Image.LANCZOS)
        thumb.save(thumb_path, quality=80, optimize=True)

        result["thumb"] = f"uploads/{subfolder}/{thumb_name}"

    return result
