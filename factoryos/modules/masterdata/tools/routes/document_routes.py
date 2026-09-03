from flask import abort, flash, redirect, request, send_file, url_for
from flask_login import login_required

from . import bp
from ..models import Tool
from ..services.tool_storage_service import (
    delete_tool_document,
    get_tool_document_path,
    save_tool_documents,
)


@bp.route("/<int:tool_id>/documents/upload", methods=["POST"])
@login_required
def upload_documents(tool_id):
    tool = Tool.query.get_or_404(tool_id)
    files = request.files.getlist("documents")

    try:
        saved = save_tool_documents(
            tool,
            files,
            category=request.form.get(
                "document_category",
                "documents"
            )
        )
    except ValueError as error:
        flash(str(error), "danger")
    else:
        if saved:
            flash(
                f"{len(saved)} Datei(en) wurden gespeichert.",
                "success"
            )
        else:
            flash("Keine Datei ausgewählt.", "danger")

    return redirect(url_for("tools.detail", tool_id=tool.id))


@bp.route(
    "/<int:tool_id>/documents/<category>/<path:filename>"
)
@login_required
def download_document(tool_id, category, filename):
    tool = Tool.query.get_or_404(tool_id)

    try:
        path = get_tool_document_path(
            tool.tool_no,
            category,
            filename
        )
    except ValueError:
        abort(404)

    if not path.is_file():
        abort(404)

    return send_file(
        path,
        as_attachment=True,
        download_name=path.name,
        conditional=True,
    )


@bp.route(
    "/<int:tool_id>/documents/<category>/<path:filename>/delete",
    methods=["POST"]
)
@login_required
def delete_document(tool_id, category, filename):
    tool = Tool.query.get_or_404(tool_id)

    try:
        deleted = delete_tool_document(
            tool.tool_no,
            category,
            filename
        )
    except ValueError:
        abort(404)

    flash(
        "Dokument wurde aus der aktiven Ablage ins Archiv verschoben."
        if deleted
        else "Dokument wurde nicht gefunden.",
        "success" if deleted else "danger"
    )

    return redirect(url_for("tools.detail", tool_id=tool.id))
