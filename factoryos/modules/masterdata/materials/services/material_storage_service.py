from datetime import datetime
from pathlib import Path

from factoryos.core.storage import (
    MATERIAL_DOCUMENT_CATEGORIES,
    MATERIAL_ROOT_PARTS,
    archive_directory,
    ensure_material_structure,
    file_size_label,
    material_category_folder,
    material_folder,
    merge_move_directory,
    move_stored_file,
    save_upload,
    storage_root,
    stored_relative_path,
)


ALLOWED_DOCUMENT_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".txt",
    ".rtf", ".odt", ".ods", ".zip", ".jpg", ".jpeg", ".png", ".webp",
}


def create_material_folders(material_no):
    return ensure_material_structure(material_no)


def get_material_storage_path(material_no):
    return stored_relative_path(material_folder(material_no))


def _validate_document(file):
    if not file or not file.filename:
        return
    extension = Path(file.filename).suffix.lower()
    if extension not in ALLOWED_DOCUMENT_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_DOCUMENT_EXTENSIONS))
        raise ValueError(
            f"Dateityp '{extension or 'ohne Endung'}' ist nicht erlaubt. Erlaubt: {allowed}"
        )


def validate_material_documents(files, category):
    if category not in MATERIAL_DOCUMENT_CATEGORIES:
        raise ValueError("Ungültige Dokumentkategorie")
    files = [file for file in (files or []) if file and file.filename]
    for file in files:
        _validate_document(file)
    return files


def save_material_documents(material, files, category):
    files = validate_material_documents(files, category)

    create_material_folders(material.material_no)
    destination = material_category_folder(material.material_no, category)
    return [save_upload(file, destination, preserve_name=True) for file in files]


def list_material_documents(material_no):
    documents = []
    for category, label in MATERIAL_DOCUMENT_CATEGORIES.items():
        folder = material_category_folder(material_no, category)
        if not folder.is_dir():
            continue
        for path in folder.iterdir():
            if not path.is_file() or path.name.startswith("."):
                continue
            stat = path.stat()
            documents.append({
                "category": category,
                "category_label": label,
                "filename": path.name,
                "size": file_size_label(stat.st_size),
                "modified_at": datetime.fromtimestamp(stat.st_mtime).strftime("%d.%m.%Y %H:%M"),
            })
    return sorted(documents, key=lambda item: (item["category_label"], item["filename"].lower()))


def get_material_document_path(material_no, category, filename):
    if category not in MATERIAL_DOCUMENT_CATEGORIES:
        raise ValueError("Ungültige Dokumentkategorie")
    if not filename or Path(filename).name != filename:
        raise ValueError("Ungültiger Dateiname")

    folder = material_category_folder(material_no, category).resolve()
    path = (folder / filename).resolve()
    try:
        path.relative_to(folder)
    except ValueError as error:
        raise ValueError("Ungültiger Dateiname") from error
    return path


def delete_material_document(material_no, category, filename):
    path = get_material_document_path(material_no, category, filename)
    if not path.is_file():
        return False

    archive = material_category_folder(material_no, "history").joinpath(
        "Geloeschte_Dokumente",
        MATERIAL_DOCUMENT_CATEGORIES[category],
    )
    move_stored_file(stored_relative_path(path), archive)
    return True


def rename_material_folder(old_material_no, new_material_no):
    if old_material_no == new_material_no:
        return
    merge_move_directory(material_folder(old_material_no), material_folder(new_material_no))
    ensure_material_structure(new_material_no)


def delete_material_folder(material_no):
    archive_root = storage_root().joinpath(
        *MATERIAL_ROOT_PARTS,
        "_Archiv",
        "Geloeschte_Materialien",
    )
    return archive_directory(material_folder(material_no), archive_root, material_no)
