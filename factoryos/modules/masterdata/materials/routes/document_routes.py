from flask import abort, flash, redirect, request, send_file, url_for
from flask_login import login_required

from factoryos.core.auth import permission_required

from ..queries.material_queries import get_material
from ..services.material_storage_service import (
    delete_material_document,
    get_material_document_path,
    save_material_documents,
)
from . import bp


@bp.route("/<int:material_id>/documents/upload", methods=["POST"])
@login_required
@permission_required("materials.documents")
def upload_documents(material_id):
    material = get_material(material_id)
    try:
        saved = save_material_documents(
            material,
            request.files.getlist("documents"),
            request.form.get("document_category", "data_sheets"),
        )
        flash(
            f"{len(saved)} Datei(en) wurden gespeichert." if saved else "Keine Datei ausgewählt.",
            "success" if saved else "danger",
        )
    except ValueError as error:
        flash(str(error), "danger")
    return redirect(url_for("materials.detail", material_id=material.id))


@bp.route("/<int:material_id>/documents/<category>/<path:filename>")
@login_required
@permission_required("materials.view")
def download_document(material_id, category, filename):
    material = get_material(material_id)
    try:
        path = get_material_document_path(material.material_no, category, filename)
    except ValueError:
        abort(404)
    if not path.is_file():
        abort(404)
    return send_file(path, as_attachment=True, download_name=path.name, conditional=True)


@bp.route("/<int:material_id>/documents/<category>/<path:filename>/delete", methods=["POST"])
@login_required
@permission_required("materials.documents")
def delete_document(material_id, category, filename):
    material = get_material(material_id)
    try:
        deleted = delete_material_document(material.material_no, category, filename)
    except ValueError:
        abort(404)
    flash(
        "Dokument wurde ins Materialarchiv verschoben." if deleted else "Dokument wurde nicht gefunden.",
        "success" if deleted else "danger",
    )
    return redirect(url_for("materials.detail", material_id=material.id))
