import shutil
import uuid
from datetime import datetime
from pathlib import Path, PurePosixPath

from flask import current_app, url_for
from werkzeug.utils import secure_filename


TOOL_ROOT_PARTS = ("Stammdaten", "Werkzeuge")

TOOL_FOLDERS = {
    "images": "Werkzeugbilder",
    "documents": "Dokumente",
    "service": "Wartung",
    "history": "Historie",
    "errors": "Werkzeugfehlermeldungen",
}

DOCUMENT_CATEGORIES = {
    "documents": "Dokumente",
    "service": "Wartung",
    "history": "Historie",
}


def storage_root():
    configured = current_app.config["FACTORYOS_STORAGE_ROOT"]
    return Path(configured).expanduser().resolve()


def _safe_segment(value, fallback="Unbekannt"):
    value = secure_filename(str(value or "")).strip("._")
    return value[:100] or fallback


def _safe_relative_path(value):
    normalized = str(value or "").replace("\\", "/").lstrip("/")
    relative = PurePosixPath(normalized)

    if not normalized or ".." in relative.parts:
        raise ValueError("Ungültiger Speicherpfad")

    return relative


def _inside(base, candidate):
    try:
        candidate.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def ensure_storage_structure():
    root = storage_root()

    folders = [
        root.joinpath(*TOOL_ROOT_PARTS),
        root.joinpath(
            *TOOL_ROOT_PARTS,
            "_Archiv",
            "Geloeschte_Werkzeuge",
        ),
        root.joinpath(
            *TOOL_ROOT_PARTS,
            "_Unzugeordnet",
            TOOL_FOLDERS["errors"],
            "_Temp",
        ),
        root.joinpath(
            *TOOL_ROOT_PARTS,
            "_Unzugeordnet",
            TOOL_FOLDERS["errors"],
            "_Altbestand",
        ),
    ]

    for folder in folders:
        folder.mkdir(parents=True, exist_ok=True)

    return root


def tool_folder(tool_no):
    return storage_root().joinpath(
        *TOOL_ROOT_PARTS,
        _safe_segment(tool_no, "Werkzeug_ohne_Nummer"),
    )


def tool_category_folder(tool_no, category):
    if category not in TOOL_FOLDERS:
        raise ValueError(f"Unbekannte Werkzeug-Ablage: {category}")

    return tool_folder(tool_no) / TOOL_FOLDERS[category]


def ensure_tool_structure(tool_no):
    base = tool_folder(tool_no)

    for folder_name in TOOL_FOLDERS.values():
        (base / folder_name).mkdir(parents=True, exist_ok=True)

    return base


def tool_error_revision_folder(tool_no, error_no, revision):
    try:
        revision_number = int(revision or 1)
    except (TypeError, ValueError):
        revision_number = 1

    return tool_category_folder(tool_no, "errors").joinpath(
        _safe_segment(error_no, "Fehlermeldung_ohne_Nummer"),
        f"Revision_{revision_number:02d}",
    )


def ensure_tool_error_structure(tool_no, error_no, revision):
    base = tool_error_revision_folder(tool_no, error_no, revision)

    for folder_name in ("Bilder", "PDF"):
        (base / folder_name).mkdir(parents=True, exist_ok=True)

    return base


def temp_tool_error_image_folder(temp_id):
    folder = storage_root().joinpath(
        *TOOL_ROOT_PARTS,
        "_Unzugeordnet",
        TOOL_FOLDERS["errors"],
        "_Temp",
        _safe_segment(temp_id, "Temp_ohne_ID"),
        "Bilder",
    )
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def legacy_tool_folder(tool_no):
    return Path(current_app.static_folder).joinpath(
        "uploads",
        "tools",
        _safe_segment(tool_no, "Werkzeug_ohne_Nummer"),
    )


def stored_relative_path(path):
    path = Path(path).resolve()
    root = storage_root()

    if not _inside(root, path):
        raise ValueError("Datei liegt außerhalb der FactoryOS-Ablage")

    return path.relative_to(root).as_posix()


def is_managed_storage_path(stored_path):
    try:
        relative = _safe_relative_path(stored_path)
    except ValueError:
        return False

    return relative.parts[:2] == TOOL_ROOT_PARTS


def resolve_stored_file(stored_path):
    relative = _safe_relative_path(stored_path)

    if is_managed_storage_path(relative.as_posix()):
        base = storage_root()
    else:
        # Rückwärtskompatibilität für bestehende static/uploads-Pfade.
        base = Path(current_app.static_folder).resolve()

    candidate = base.joinpath(*relative.parts)

    if not _inside(base, candidate):
        raise ValueError("Ungültiger Speicherpfad")

    return candidate


def storage_url(stored_path):
    if not stored_path:
        return ""

    normalized = str(stored_path).replace("\\", "/")

    if is_managed_storage_path(normalized):
        return url_for(
            "core.storage_file",
            storage_path=normalized,
        )

    return url_for("static", filename=normalized)


def _unique_destination(directory, original_name, generated_prefix=False):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)

    safe_name = secure_filename(original_name or "Datei")
    stem = Path(safe_name).stem[:90] or "Datei"
    suffix = Path(safe_name).suffix.lower()[:12]

    if generated_prefix:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stem = f"{stamp}_{uuid.uuid4().hex[:8]}_{stem}"

    candidate = directory / f"{stem}{suffix}"
    counter = 2

    while candidate.exists():
        candidate = directory / f"{stem}_{counter}{suffix}"
        counter += 1

    return candidate


def save_upload(upload, directory, preserve_name=False):
    if not upload or not upload.filename:
        return None

    destination = _unique_destination(
        directory,
        upload.filename,
        generated_prefix=not preserve_name,
    )
    upload.save(destination)
    return stored_relative_path(destination)


def copy_stored_file(stored_path, directory, preferred_name=None):
    source = resolve_stored_file(stored_path)

    if not source.is_file():
        return stored_path

    destination = _unique_destination(
        directory,
        preferred_name or source.name,
        generated_prefix=False,
    )
    shutil.copy2(source, destination)
    return stored_relative_path(destination)


def move_stored_file(stored_path, directory, preferred_name=None):
    source = resolve_stored_file(stored_path)

    if not source.is_file():
        return stored_path

    destination = _unique_destination(
        directory,
        preferred_name or source.name,
        generated_prefix=False,
    )
    shutil.move(str(source), str(destination))
    return stored_relative_path(destination)


def delete_stored_file(stored_path):
    if not stored_path:
        return False

    path = resolve_stored_file(stored_path)

    if path.is_file():
        path.unlink()
        return True

    return False


def merge_move_directory(source, destination):
    source = Path(source)
    destination = Path(destination)

    if not source.exists() or source.resolve() == destination.resolve():
        return destination

    destination.mkdir(parents=True, exist_ok=True)

    for item in source.iterdir():
        target = destination / item.name

        if item.is_dir():
            merge_move_directory(item, target)
            continue

        if target.exists():
            target = _unique_destination(
                destination,
                item.name,
                generated_prefix=False,
            )

        shutil.move(str(item), str(target))

    try:
        source.rmdir()
    except OSError:
        pass

    return destination


def archive_directory(source, archive_root, label):
    source = Path(source)

    if not source.exists():
        return None

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destination = _unique_destination(
        archive_root,
        f"{stamp}_{_safe_segment(label)}",
        generated_prefix=False,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(destination))
    return destination


def file_size_label(size):
    size = int(size or 0)

    if size < 1024:
        return f"{size} B"

    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"

    return f"{size / (1024 * 1024):.1f} MB"
