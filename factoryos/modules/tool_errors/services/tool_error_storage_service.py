from datetime import datetime

from factoryos.core.storage import (
    archive_directory,
    copy_stored_file,
    delete_stored_file,
    ensure_tool_error_structure,
    file_size_label,
    move_stored_file,
    save_upload,
    stored_relative_path,
    temp_tool_error_image_folder,
    tool_error_revision_folder,
)


def _tool_no(error):
    tool = getattr(error, "tool", None)

    if tool and tool.tool_no:
        return tool.tool_no

    from factoryos.modules.masterdata.tools.models import Tool

    tool = Tool.query.get(error.tool_id)

    if not tool:
        raise ValueError("Werkzeug der Fehlermeldung wurde nicht gefunden")

    return tool.tool_no


def create_tool_error_folders(error):
    return ensure_tool_error_structure(
        _tool_no(error),
        error.error_no,
        error.revision,
    )


def get_tool_error_storage_path(error):
    return stored_relative_path(
        tool_error_revision_folder(
            _tool_no(error),
            error.error_no,
            error.revision,
        )
    )


def list_tool_error_pdfs(error):
    folder = tool_error_revision_folder(
        _tool_no(error),
        error.error_no,
        error.revision,
    ) / "PDF"

    if not folder.is_dir():
        return []

    pdfs = []

    for path in folder.glob("*.pdf"):
        if not path.is_file():
            continue

        stat = path.stat()
        pdfs.append({
            "filename": path.name,
            "path": stored_relative_path(path),
            "size": file_size_label(stat.st_size),
            "modified_at": datetime.fromtimestamp(
                stat.st_mtime
            ).strftime("%d.%m.%Y %H:%M"),
        })

    return sorted(
        pdfs,
        key=lambda item: item["modified_at"],
        reverse=True,
    )


def save_tool_error_image(file, temp_id=None, error=None):
    if error:
        destination = create_tool_error_folders(error) / "Bilder"
    else:
        if not temp_id:
            raise ValueError("Temporäre Bild-ID fehlt")

        destination = temp_tool_error_image_folder(temp_id)

    return save_upload(
        file,
        destination,
        preserve_name=False,
    )


def move_image_to_error(image, error):
    destination = create_tool_error_folders(error) / "Bilder"
    image.image_path = move_stored_file(
        image.image_path,
        destination,
    )
    image.tool_error_id = error.id
    image.temp_id = None
    return image.image_path


def copy_image_to_error(image, error):
    destination = create_tool_error_folders(error) / "Bilder"
    return copy_stored_file(
        image.image_path,
        destination,
    )


def delete_tool_error_image_file(image):
    return delete_stored_file(image.image_path)


def archive_tool_error_pdf(error, pdf_bytes):
    destination = create_tool_error_folders(error) / "PDF"
    safe_error_no = tool_error_revision_folder(
        _tool_no(error),
        error.error_no,
        error.revision,
    ).parent.name
    filename = (
        f"Fehlermeldung_{safe_error_no}_"
        f"Revision_{int(error.revision or 1):02d}.pdf"
    )
    final_path = destination / filename
    temp_path = destination / f".{filename}.tmp"

    temp_path.write_bytes(pdf_bytes)
    temp_path.replace(final_path)
    return stored_relative_path(final_path)


def archive_tool_error_revision(error):
    tool_no = _tool_no(error)
    source = tool_error_revision_folder(
        tool_no,
        error.error_no,
        error.revision,
    )
    archive_root = source.parent / "_Archiv"

    archived = archive_directory(
        source,
        archive_root,
        f"Revision_{int(error.revision or 1):02d}",
    )

    if not archived:
        # Falls noch keine neue Ablage vorhanden ist, wird für Altbilder ein
        # eigener Archivordner vorbereitet.
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archived = archive_root / (
            f"{stamp}_Revision_{int(error.revision or 1):02d}"
        )

    # Noch nicht migrierte Altbilder können parallel zu einem neuen PDF-Ordner
    # existieren. Auch diese Dateien werden deshalb ins Archiv übernommen.
    image_folder = archived / "Bilder"

    moved = False

    for image in list(error.images or []):
        new_path = move_stored_file(
            image.image_path,
            image_folder,
        )

        if new_path != image.image_path:
            moved = True

    return archived if archived.exists() or moved else None


def move_tool_error_revision(error, old_tool_no, new_tool_no):
    if old_tool_no == new_tool_no:
        return

    from factoryos.core.storage import merge_move_directory

    old_folder = tool_error_revision_folder(
        old_tool_no,
        error.error_no,
        error.revision,
    )
    new_folder = tool_error_revision_folder(
        new_tool_no,
        error.error_no,
        error.revision,
    )

    old_prefix = stored_relative_path(old_folder).rstrip("/") + "/"
    new_prefix = stored_relative_path(new_folder).rstrip("/") + "/"

    merge_move_directory(old_folder, new_folder)
    ensure_tool_error_structure(
        new_tool_no,
        error.error_no,
        error.revision,
    )

    for image in error.images or []:
        normalized = (image.image_path or "").replace("\\", "/")

        if normalized.startswith(old_prefix):
            image.image_path = normalized.replace(
                old_prefix,
                new_prefix,
                1,
            )
