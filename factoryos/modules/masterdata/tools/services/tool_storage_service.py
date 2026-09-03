from datetime import datetime
from pathlib import Path

from factoryos.core.storage import (
    DOCUMENT_CATEGORIES,
    TOOL_ROOT_PARTS,
    archive_directory,
    ensure_tool_structure,
    file_size_label,
    legacy_tool_folder,
    merge_move_directory,
    move_stored_file,
    save_upload,
    storage_root,
    stored_relative_path,
    tool_category_folder,
    tool_folder,
)
from factoryos.extensions import db
from factoryos.modules.masterdata.tools.models import ToolImage


ALLOWED_DOCUMENT_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".csv",
    ".txt",
    ".rtf",
    ".odt",
    ".ods",
    ".zip",
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}


def get_tool_base_folder(tool_no):
    return str(tool_folder(tool_no))


def get_tool_image_folder(tool_no):
    return str(tool_category_folder(tool_no, "images"))


def get_tool_document_folder(tool_no, category="documents"):
    if category not in DOCUMENT_CATEGORIES:
        raise ValueError("Ungültige Dokumentkategorie")

    return str(tool_category_folder(tool_no, category))


def create_tool_folders(tool_no):
    return ensure_tool_structure(tool_no)


def get_tool_storage_path(tool_no):
    return stored_relative_path(tool_folder(tool_no))


def save_tool_image(tool, file, title=None, description=None):
    if not file or not file.filename:
        return None

    create_tool_folders(tool.tool_no)
    image_path = save_upload(
        file,
        tool_category_folder(tool.tool_no, "images"),
        preserve_name=False,
    )

    image = ToolImage(
        tool_id=tool.id,
        image_path=image_path,
        title=title,
        description=description,
        sort_order=0,
        is_primary=False,
    )
    db.session.add(image)
    return image


def save_tool_images(tool, files):
    saved = []

    for file in files or []:
        image = save_tool_image(tool, file)

        if image:
            saved.append(image)

    return saved


def _validate_document(file):
    if not file or not file.filename:
        return

    extension = Path(file.filename).suffix.lower()

    if extension not in ALLOWED_DOCUMENT_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_DOCUMENT_EXTENSIONS))
        raise ValueError(
            f"Dateityp '{extension or 'ohne Endung'}' ist nicht erlaubt. "
            f"Erlaubt: {allowed}"
        )


def validate_tool_documents(files, category="documents"):
    if category not in DOCUMENT_CATEGORIES:
        raise ValueError("Ungültige Dokumentkategorie")

    files = [file for file in (files or []) if file and file.filename]

    for file in files:
        _validate_document(file)

    return files


def save_tool_documents(tool, files, category="documents"):
    files = validate_tool_documents(files, category)

    create_tool_folders(tool.tool_no)
    destination = tool_category_folder(tool.tool_no, category)

    return [
        save_upload(file, destination, preserve_name=True)
        for file in files
    ]


def list_tool_documents(tool_no):
    documents = []

    for category, label in DOCUMENT_CATEGORIES.items():
        folder = tool_category_folder(tool_no, category)

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
                "modified_at": datetime.fromtimestamp(
                    stat.st_mtime
                ).strftime("%d.%m.%Y %H:%M"),
            })

    return sorted(
        documents,
        key=lambda item: (
            item["category_label"].lower(),
            item["filename"].lower(),
        ),
    )


def get_tool_document_path(tool_no, category, filename):
    if category not in DOCUMENT_CATEGORIES:
        raise ValueError("Ungültige Dokumentkategorie")

    if not filename or Path(filename).name != filename:
        raise ValueError("Ungültiger Dateiname")

    folder = tool_category_folder(tool_no, category).resolve()
    path = (folder / filename).resolve()

    try:
        path.relative_to(folder)
    except ValueError as error:
        raise ValueError("Ungültiger Dateiname") from error

    return path


def delete_tool_document(tool_no, category, filename):
    path = get_tool_document_path(tool_no, category, filename)

    if path.is_file():
        archive = tool_category_folder(
            tool_no,
            "history",
        ).joinpath(
            "Geloeschte_Dokumente",
            DOCUMENT_CATEGORIES[category],
        )
        move_stored_file(
            stored_relative_path(path),
            archive,
        )
        return True

    return False


def delete_tool_image(image):
    if not image:
        return

    tool = getattr(image, "tool", None)

    if tool and tool.tool_no:
        archive = tool_category_folder(
            tool.tool_no,
            "history",
        ) / "Geloeschte_Werkzeugbilder"
        move_stored_file(image.image_path, archive)

    db.session.delete(image)


def delete_tool_images_by_ids(image_ids):
    for image_id in image_ids or []:
        image = ToolImage.query.get(image_id)

        if image:
            delete_tool_image(image)


def delete_tool_folder(tool_no):
    archive_root = storage_root().joinpath(
        *TOOL_ROOT_PARTS,
        "_Archiv",
        "Geloeschte_Werkzeuge",
    )
    archived = archive_directory(
        tool_folder(tool_no),
        archive_root,
        tool_no,
    )

    legacy = legacy_tool_folder(tool_no)

    if legacy.exists():
        if archived:
            merge_move_directory(
                legacy,
                archived / "Altbestand_static_uploads",
            )
        else:
            archived = archive_directory(
                legacy,
                archive_root,
                f"{tool_no}_Altbestand",
            )

    return archived


def rename_tool_folder(old_tool_no, new_tool_no):
    if old_tool_no == new_tool_no:
        return

    old_folder = tool_folder(old_tool_no)
    new_folder = tool_folder(new_tool_no)
    merge_move_directory(old_folder, new_folder)
    ensure_tool_structure(new_tool_no)

    old_legacy = legacy_tool_folder(old_tool_no)
    new_legacy = legacy_tool_folder(new_tool_no)
    merge_move_directory(old_legacy, new_legacy)

    old_storage_prefix = stored_relative_path(old_folder).rstrip("/") + "/"
    new_storage_prefix = stored_relative_path(new_folder).rstrip("/") + "/"
    old_legacy_prefix = f"uploads/tools/{old_folder.name}/"
    new_legacy_prefix = f"uploads/tools/{new_folder.name}/"

    images = (
        ToolImage.query
        .join(ToolImage.tool)
        .filter_by(tool_no=new_tool_no)
        .all()
    )

    for image in images:
        normalized = (image.image_path or "").replace("\\", "/")

        if normalized.startswith(old_storage_prefix):
            image.image_path = normalized.replace(
                old_storage_prefix,
                new_storage_prefix,
                1,
            )
        elif normalized.startswith(old_legacy_prefix):
            image.image_path = normalized.replace(
                old_legacy_prefix,
                new_legacy_prefix,
                1,
            )

    from factoryos.modules.masterdata.tools.models import Tool
    from factoryos.modules.tool_errors.models import ToolError, ToolErrorImage

    tool = Tool.query.filter_by(tool_no=new_tool_no).first()

    if not tool:
        return

    error_images = (
        ToolErrorImage.query
        .join(ToolErrorImage.tool_error)
        .filter(ToolError.tool_id == tool.id)
        .all()
    )

    for image in error_images:
        normalized = (image.image_path or "").replace("\\", "/")

        if normalized.startswith(old_storage_prefix):
            image.image_path = normalized.replace(
                old_storage_prefix,
                new_storage_prefix,
                1,
            )
