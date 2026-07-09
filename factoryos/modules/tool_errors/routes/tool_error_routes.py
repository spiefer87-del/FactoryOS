#factoryos/modules/tool_errors/routes/tool_error_routes.py
import os

from flask import (
    render_template,
    request,
    redirect,
    url_for,
    jsonify,
    make_response,
    flash
)

from flask_login import login_required, current_user

from factoryos.extensions import db
from factoryos.core.auth import permission_required, has_permission
from factoryos.core.models.change_log import ChangeLog

from . import bp

from ..models import ToolError, ToolErrorImage

from ..queries.tool_error_queries import (
    get_tool_errors,
    get_tool_error
)

from ..services.tool_error_service import (
    create_tool_error,
    update_tool_error,
    delete_tool_error,
    upload_image,
    assign_images_to_error,
    set_tool_status,
    generate_tool_error_pdf
)

from ..services.workflow_service import (
    start_review,
    release,
    close,
    create_revision,
    get_current_revision,
    get_revisions,
    return_to_draft,
    can_edit,
    can_start_review,
    can_release,
    can_close,
    can_create_revision,
    can_return_to_draft,
    ensure_editable
)

from ..constants import (
    WORKFLOW_STATUSES,
    WORKFLOW_STATUS_COLORS
)

from factoryos.modules.masterdata.tools.queries.tool_queries import get_all_tools
from factoryos.modules.tool_errors.models import ToolErrorTitlePreset
from factoryos.modules.masterdata.shared.constants import TOOL_STATUSES




# =========================
# DASHBOARD
# =========================
@bp.route("/")
@login_required
@permission_required("tool_error.view")
def dashboard():

    errors = get_tool_errors(
        include_history=False
    )

    return render_template(
        "tool_errors/dashboard.html",
        errors=errors,
        WORKFLOW_STATUSES=WORKFLOW_STATUSES,
        WORKFLOW_STATUS_COLORS=WORKFLOW_STATUS_COLORS
    )
    

# =========================
# LISTE
# =========================
@bp.route("/list")
@login_required
@permission_required("tool_error.view")
def list_errors():

    errors = get_tool_errors(
        include_history=False
    )

    return render_template(
        "tool_errors/list.html",
        errors=errors,

        WORKFLOW_STATUSES=WORKFLOW_STATUSES,
        WORKFLOW_STATUS_COLORS=WORKFLOW_STATUS_COLORS,

        can_create_error=has_permission(
            current_user,
            "tool_error.create"
        ),

        can_delete_errors=has_permission(
            current_user,
            "tool_error.delete"
        ),

        can_export_pdf=has_permission(
            current_user,
            "tool_error.pdf_export"
        )
    )

# =========================
# CREATE
# =========================

@bp.route("/create", methods=["GET", "POST"])
@login_required
@permission_required("tool_error.create")
def create():

    tools = get_all_tools()

    presets = (
        ToolErrorTitlePreset.query
        .order_by(ToolErrorTitlePreset.title)
        .all()
    )

    if request.method == "POST":

        try:

            error = create_tool_error(
                request.form,
                current_user.id
            )

            assign_images_to_error(
                temp_id=request.form.get("temp_id"),
                error_id=error.id
            )

            flash(
                "Fehlermeldung wurde erstellt.",
                "success"
            )

            return redirect(
                url_for(
                    "tool_error.detail",
                    error_id=error.id,
                    new=1
                )
            )

        except Exception as e:

            flash(
                f"Fehlermeldung konnte nicht erstellt werden: {e}",
                "danger"
            )

            return redirect(request.url)

    return render_template(
        "tool_errors/create.html",
        tools=tools,
        presets=presets,
        TOOL_STATUSES=TOOL_STATUSES,
        error=None
    )


# =========================
# DETAIL
# =========================

@bp.route("/<int:error_id>")
@login_required
@permission_required("tool_error.view")
def detail(error_id):

    error = get_tool_error(error_id)

    revisions = get_revisions(error)

    revision_ids = [
        revision.id
        for revision in revisions
    ]

    if not revision_ids:
        revision_ids = [error.id]

    limit = request.args.get(
        "limit",
        "5"
    )

    log_query = (
        ChangeLog.query
        .filter(
            ChangeLog.entity_type == "tool_error",
            ChangeLog.entity_id.in_(revision_ids)
        )
        .order_by(
            ChangeLog.created_at.desc()
        )
    )

    if limit == "all":

        logs = log_query.all()

    else:

        try:
            limit_int = int(limit)
        except ValueError:
            limit_int = 5

        logs = log_query.limit(limit_int).all()

    return render_template(
        "tool_errors/detail.html",
        error=error,
        revisions=revisions,
        logs=logs,
    
        TOOL_STATUSES=TOOL_STATUSES,
        WORKFLOW_STATUSES=WORKFLOW_STATUSES,
        WORKFLOW_STATUS_COLORS=WORKFLOW_STATUS_COLORS,
    
        can_edit_error=(
            can_edit(error)
            and has_permission(current_user, "tool_error.edit")
        ),
    
        can__review=(
            can_start_review(error)
            and has_permission(current_user, "tool_error._review")
        ),
    
        can_return_to_draft=(
            can_return_to_draft(error)
            and has_permission(current_user, "tool_error.return_to_draft")
        ),
    
        can_release_error=(
            can_release(error)
            and has_permission(current_user, "tool_error.release")
        ),
    
        can_close_error=(
            can_close(error)
            and has_permission(current_user, "tool_error.close")
        ),
    
        can_create_revision=(
            can_create_revision(error)
            and has_permission(current_user, "tool_error.revision")
        ),
    
        can_delete_error=(
            can_edit(error)
            and has_permission(current_user, "tool_error.delete")
        ),
    
        can_export_pdf=has_permission(
            current_user,
            "tool_error.pdf_export"
        )
    )


# =========================
# EDIT
# =========================

@bp.route("/<int:error_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("tool_error.edit")
def edit(error_id):

    error = get_tool_error(error_id)

    if not can_edit(error):

        flash(
            "Diese Fehlermeldung ist gesperrt. Bitte zur Bearbeitung zurückgeben oder eine neue Revision erstellen.",
            "danger"
        )

        return redirect(
            url_for(
                "tool_error.detail",
                error_id=error.id
            )
        )

    tools = get_all_tools()

    presets = (
        ToolErrorTitlePreset.query
        .order_by(ToolErrorTitlePreset.title)
        .all()
    )

    if request.method == "POST":

        try:

            update_tool_error(
                error,
                request.form
            )

            assign_images_to_error(
                temp_id=request.form.get("temp_id"),
                error_id=error.id
            )

            flash(
                "Fehlermeldung wurde aktualisiert.",
                "success"
            )

            return redirect(
                url_for(
                    "tool_error.detail",
                    error_id=error.id
                )
            )

        except PermissionError as e:

            flash(
                str(e),
                "danger"
            )

            return redirect(
                url_for(
                    "tool_error.detail",
                    error_id=error.id
                )
            )

        except Exception as e:

            flash(
                f"Fehlermeldung konnte nicht gespeichert werden: {e}",
                "danger"
            )

            return redirect(request.url)

    return render_template(
        "tool_errors/edit.html",
        error=error,
        tools=tools,
        presets=presets,
        TOOL_STATUSES=TOOL_STATUSES
    )


# =========================
# TEMP / IMAGE UPLOAD
# =========================

@bp.route("/upload_temp_image", methods=["POST"])
@login_required
@permission_required("tool_error.edit")
def upload_temp():

    try:

        image = upload_image(
            file=request.files.get("image"),
            marker_x=request.form.get("marker_x"),
            marker_y=request.form.get("marker_y"),
            marker_px=request.form.get("marker_px"),
            marker_py=request.form.get("marker_py"),
            description=request.form.get("description"),
            temp_id=request.form.get("temp_id"),
            tool_error_id=request.form.get("tool_error_id")
        )

    except PermissionError as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 403

    except Exception as e:

        return jsonify({
            "success": False,
            "error": f"Upload fehlgeschlagen: {e}"
        }), 500

    if not image:

        return jsonify({
            "success": False,
            "error": "Upload fehlgeschlagen"
        }), 400

    html = render_template(
        "components/image_card.html",
        image=image,
        editable=True,
        marker_number=1
    )

    return jsonify({
        "success": True,
        "image_id": image.id,
        "html": html
    })


# =========================
# IMAGE DELETE
# =========================

@bp.route("/delete_temp_image/<int:image_id>", methods=["POST"])
@login_required
@permission_required("tool_error.edit")
def delete_temp_image(image_id):

    image = ToolErrorImage.query.get_or_404(image_id)

    try:

        if image.tool_error_id:

            error = ToolError.query.get(image.tool_error_id)

            if error:
                ensure_editable(error)

        image_path = os.path.join(
            "uploads",
            "tool_errors",
            os.path.basename(image.image_path)
        )

        full_path = os.path.join(
            os.getcwd(),
            "factoryos",
            "static",
            image_path
        )

        same_file_used = (
            ToolErrorImage.query
            .filter(
                ToolErrorImage.image_path == image.image_path,
                ToolErrorImage.id != image.id
            )
            .count()
        )

        if same_file_used == 0 and os.path.exists(full_path):
            os.remove(full_path)

        db.session.delete(image)
        db.session.commit()

        return jsonify({
            "success": True
        })

    except PermissionError as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 403

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# =========================
# IMAGE GET
# =========================

@bp.route("/image/<int:image_id>")
@login_required
def get_image(image_id):

    image = ToolErrorImage.query.get_or_404(image_id)

    return jsonify({
        "id": image.id,
        "image_url": url_for(
            "static",
            filename=image.image_path
        ),
        "marker_x": image.marker_x,
        "marker_y": image.marker_y,
        "marker_px": image.marker_px,
        "marker_py": image.marker_py,
        "description": image.description
    })


# =========================
# MARKER UPDATE
# =========================

@bp.route("/image/<int:image_id>/marker", methods=["POST"])
@login_required
@permission_required("tool_error.edit")
def update_marker(image_id):

    image = ToolErrorImage.query.get_or_404(image_id)

    try:

        if image.tool_error_id:

            error = ToolError.query.get(image.tool_error_id)

            if error:
                ensure_editable(error)

        data = request.get_json() or {}

        image.marker_x = float(data["marker_x"])
        image.marker_y = float(data["marker_y"])

        image.marker_px = int(data["marker_px"])
        image.marker_py = int(data["marker_py"])

        image.description = data.get(
            "description",
            image.description
        )

        db.session.commit()

        return jsonify({
            "success": True
        })

    except PermissionError as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 403

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# =========================
# START REVIEW
# =========================

@bp.route("/<int:error_id>/start-review")
@login_required
@permission_required("tool_error.submit_review")
def start_review_route(error_id):

    error = get_tool_error(error_id)

    try:

        start_review(
            error,
            current_user.id
        )

        flash(
            "Fehlermeldung wurde zur Prüfung eingereicht.",
            "success"
        )

    except PermissionError as e:

        flash(
            str(e),
            "danger"
        )

    return redirect(
        url_for(
            "tool_error.detail",
            error_id=error.id
        )
    )


# =========================
# RETURN TO DRAFT
# =========================

@bp.route("/<int:error_id>/return-to-draft")
@login_required
@permission_required("tool_error.return_to_draft")
def return_to_draft_route(error_id):

    error = get_tool_error(error_id)

    try:

        return_to_draft(
            error,
            current_user.id
        )

        flash(
            "Fehlermeldung wurde zur Bearbeitung zurückgegeben. Nach Änderungen muss sie erneut zur Prüfung eingereicht werden.",
            "success"
        )

    except PermissionError as e:

        flash(
            str(e),
            "danger"
        )

    return redirect(
        url_for(
            "tool_error.detail",
            error_id=error.id
        )
    )


# =========================
# RELEASE
# =========================

@bp.route("/<int:error_id>/release")
@login_required
@permission_required("tool_error.release")
def release_route(error_id):

    error = get_tool_error(error_id)

    try:

        release(
            error,
            current_user.id
        )

        flash(
            "Fehlermeldung wurde freigegeben.",
            "success"
        )

    except PermissionError as e:

        flash(
            str(e),
            "danger"
        )

    return redirect(
        url_for(
            "tool_error.detail",
            error_id=error.id
        )
    )


# =========================
# CLOSE
# =========================

@bp.route("/<int:error_id>/close")
@login_required
@permission_required("tool_error.close")
def close_route(error_id):

    error = get_tool_error(error_id)

    try:

        close(
            error,
            current_user.id
        )

        flash(
            "Fehlermeldung wurde geschlossen.",
            "success"
        )

    except PermissionError as e:

        flash(
            str(e),
            "danger"
        )

    return redirect(
        url_for(
            "tool_error.detail",
            error_id=error.id
        )
    )


# =========================
# NEW REVISION
# =========================

@bp.route("/<int:error_id>/new-revision")
@login_required
@permission_required("tool_error.revision")
def new_revision(error_id):

    error = get_tool_error(error_id)

    current = get_current_revision(error)

    if not can_create_revision(current):

        flash(
            "Eine neue Revision kann nur aus einer freigegebenen oder geschlossenen Version erstellt werden.",
            "danger"
        )

        return redirect(
            url_for(
                "tool_error.detail",
                error_id=current.id
            )
        )

    try:

        revision = create_revision(
            current,
            current_user.id
        )

        flash(
            f"Neue Revision {revision.revision} wurde erstellt.",
            "success"
        )

        return redirect(
            url_for(
                "tool_error.edit",
                error_id=revision.id
            )
        )

    except PermissionError as e:

        flash(
            str(e),
            "danger"
        )

        return redirect(
            url_for(
                "tool_error.detail",
                error_id=current.id
            )
        )


# =========================
# TOOL STATUS
# =========================

@bp.route("/<int:error_id>/set-tool-status", methods=["POST"])
@login_required
def set_tool_status_route(error_id):

    error = get_tool_error(error_id)

    try:

        ensure_editable(error)

        status = request.form.get("tool_status")

        if not status and request.is_json:
            status = request.json.get("tool_status")

        if not status:
            flash(
                "Kein Werkzeugstatus übergeben.",
                "danger"
            )

            return redirect(
                url_for(
                    "tool_error.detail",
                    error_id=error.id
                )
            )

        set_tool_status(
            error.id,
            status
        )

        flash(
            "Werkzeugstatus wurde aktualisiert.",
            "success"
        )

    except PermissionError as e:

        flash(
            str(e),
            "danger"
        )

    return redirect(
        url_for(
            "tool_error.detail",
            error_id=error.id
        )
    )


# =========================
# DELETE
# =========================

@bp.route("/<int:error_id>/delete", methods=["POST"])
@login_required
@permission_required("tool_error.delete")
def delete(error_id):

    error = get_tool_error(error_id)

    try:

        delete_tool_error(error)

        flash(
            "Fehlermeldung wurde gelöscht.",
            "success"
        )

        return redirect(
            url_for("tool_error.list_errors")
        )

    except PermissionError as e:

        flash(
            str(e),
            "danger"
        )

        return redirect(
            url_for(
                "tool_error.detail",
                error_id=error.id
            )
        )


# =========================
# PDF EXPORT
# =========================

@bp.route("/<int:error_id>/export-pdf")
@login_required
@permission_required("tool_error.pdf_export")
def export_pdf(error_id):

    error = get_tool_error(error_id)

    pdf = generate_tool_error_pdf(error)

    response = make_response(
        pdf.getvalue()
    )

    response.headers["Content-Type"] = "application/pdf"

    response.headers["Content-Disposition"] = (
        f"inline; filename={error.error_no}.pdf"
    )

    return response



